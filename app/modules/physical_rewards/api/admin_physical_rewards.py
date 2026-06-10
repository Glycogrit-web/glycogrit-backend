"""
Admin Physical Reward Management Endpoints
For bulk reward management, Excel export/import, and tracking visibility control
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.enums import RewardStatus
from app.core.rate_limit import RateLimits, limiter
from app.models.user import User
from app.models.user_reward import UserReward
from app.modules.physical_rewards.schemas.physical_reward_schemas import (
    ImportTrackingResponse,
    MarkEligibleRequest,
    MarkEligibleResponse,
    RewardWithTrackingStatus,
    ToggleVisibilityRequest,
    ToggleVisibilityResponse,
    TrackingPreviewResponse,
    UpdateTrackingRequest,
)
from app.modules.physical_rewards.services.excel_export_service import ExcelExportService
from app.modules.physical_rewards.services.excel_import_service import ExcelImportService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/physical-rewards",
    tags=["Admin - Physical Rewards"],
)


@router.post("/events/{event_id}/mark-eligible", response_model=MarkEligibleResponse)
@limiter.limit(RateLimits.DEFAULT)
async def mark_rewards_eligible(
    request: Request,
    response: Response,
    event_id: int,
    body: MarkEligibleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark physical rewards as eligible (LOCKED → READY_TO_SHIP)

    Admin marks users eligible for physical rewards after they complete target distance.
    Validates user progress before marking eligible.

    Args:
        event_id: Event ID
        body: Request with list of reward IDs
        current_user: Authenticated admin user
        db: Database session

    Returns:
        MarkEligibleResponse with counts and errors
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    marked_count = 0
    skipped_count = 0
    errors = []

    for reward_id in body.reward_ids:
        try:
            reward = db.query(UserReward).filter(
                UserReward.id == reward_id,
                UserReward.event_id == event_id
            ).first()

            if not reward:
                errors.append(f"Reward {reward_id} not found")
                skipped_count += 1
                continue

            if reward.status != RewardStatus.LOCKED:
                errors.append(
                    f"Reward {reward_id} has status '{reward.status.value}', expected 'locked'"
                )
                skipped_count += 1
                continue

            if not reward.requires_shipping:
                errors.append(f"Reward {reward_id} doesn't require shipping")
                skipped_count += 1
                continue

            # Mark as eligible
            reward.status = RewardStatus.READY_TO_SHIP
            reward.is_unlocked = True
            reward.unlocked_by_admin_id = current_user.id
            reward.unlocked_at = func.now()

            marked_count += 1
            logger.info(f"✓ Marked reward {reward_id} as eligible by admin {current_user.email}")

        except Exception as e:
            error_msg = f"Reward {reward_id}: {str(e)}"
            errors.append(error_msg)
            skipped_count += 1
            logger.error(f"❌ {error_msg}")

    db.commit()

    logger.info(
        f"📦 Mark eligible complete: {marked_count} marked, {skipped_count} skipped"
    )

    return MarkEligibleResponse(
        marked_count=marked_count,
        skipped_count=skipped_count,
        errors=errors
    )


@router.get("/events/{event_id}/export-shipping")
@limiter.limit(RateLimits.DEFAULT)
async def export_shipping_details(
    request: Request,
    response: Response,
    event_id: int,
    status_filter: Optional[str] = "ready_to_ship",
    reward_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export shipping details to Excel (Shiprocket 48-column format)

    Generates Excel file with all shipping details in exact Shiprocket bulk order format.
    Admin can download this and upload directly to Shiprocket portal.

    Args:
        event_id: Event ID
        status_filter: Filter by status (default: ready_to_ship)
        reward_type: Optional filter by reward type
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Excel file download
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        # Convert status string to enum
        reward_status = RewardStatus(status_filter) if status_filter else None

        # Export to Excel
        export_service = ExcelExportService(db)
        excel_bytes = export_service.export_shipping_details(
            event_id=event_id,
            status=reward_status,
            reward_type=reward_type
        )

        # Generate filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"shiprocket_bulk_orders_event_{event_id}_{timestamp}.xlsx"

        logger.info(f"📤 Exported shipping details for event {event_id} by admin {current_user.email}")

        return StreamingResponse(
            iter([excel_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ Export failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.post("/events/{event_id}/import-tracking", response_model=ImportTrackingResponse)
@limiter.limit(RateLimits.DEFAULT)
async def import_tracking_data(
    request: Request,
    response: Response,
    event_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import tracking data from Excel/CSV

    Expected columns (flexible matching):
    - Order Reference OR Reward ID (to match reward)
    - Tracking ID (required)
    - Tracking URL (optional)
    - Courier Name (optional)

    Processing:
    - Finds rewards by order reference or ID
    - Updates tracking fields
    - Changes status to TRACKING_ORDER
    - Makes tracking visible to users

    Args:
        event_id: Event ID
        file: Excel or CSV file with tracking data
        current_user: Authenticated admin user
        db: Database session

    Returns:
        ImportTrackingResponse with statistics
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided"
        )

    filename_lower = file.filename.lower()
    is_excel = filename_lower.endswith(('.xlsx', '.xls'))
    is_csv = filename_lower.endswith('.csv')

    if not (is_excel or is_csv):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be CSV (.csv) or Excel (.xlsx/.xls)"
        )

    # Read file content
    content = await file.read()

    # Validate file size (10MB max)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 10MB)"
        )

    try:
        # Import tracking data
        import_service = ExcelImportService(db)
        stats = import_service.import_tracking_data(
            event_id=event_id,
            file_content=content,
            filename=file.filename,
            admin_id=current_user.id
        )

        logger.info(
            f"📥 Imported tracking data for event {event_id} by admin {current_user.email}"
        )

        return ImportTrackingResponse(
            message=f"{'Excel' if is_excel else 'CSV'} file processed successfully",
            **stats
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ Import failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.patch("/{reward_id}/toggle-tracking-visibility")
@limiter.limit(RateLimits.DEFAULT)
async def toggle_tracking_visibility(
    request: Request,
    response: Response,
    reward_id: UUID,
    visible: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Toggle tracking visibility for a single reward

    Allows admin to show/hide tracking from user view.
    - If visible=False: TRACKING_ORDER → READY_TO_SHIP (hide tracking)
    - If visible=True: READY_TO_SHIP → TRACKING_ORDER (show tracking)

    Args:
        reward_id: Reward ID
        visible: Whether tracking should be visible to user
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Success response with updated status
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Get reward
    reward = db.query(UserReward).filter(UserReward.id == reward_id).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    # Check if tracking data exists
    if not reward.manual_tracking_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tracking data available for this reward"
        )

    # Update visibility and status
    reward.tracking_visible_to_user = visible

    if visible:
        reward.status = RewardStatus.TRACKING_ORDER
    else:
        reward.status = RewardStatus.READY_TO_SHIP

    db.commit()
    db.refresh(reward)

    action = "shown" if visible else "hidden"
    logger.info(
        f"👁️  Admin {current_user.email} {action} tracking for reward {reward_id}"
    )

    return {
        "success": True,
        "reward_id": str(reward_id),
        "status": reward.status.value,
        "tracking_visible": visible
    }


@router.post("/events/{event_id}/bulk-toggle-tracking", response_model=ToggleVisibilityResponse)
@limiter.limit(RateLimits.DEFAULT)
async def bulk_toggle_tracking_visibility(
    request: Request,
    response: Response,
    event_id: int,
    body: ToggleVisibilityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Toggle tracking visibility for multiple rewards

    Bulk operation to show/hide tracking for multiple rewards at once.

    Args:
        event_id: Event ID
        body: Request with reward IDs and visibility flag
        current_user: Authenticated admin user
        db: Database session

    Returns:
        ToggleVisibilityResponse with counts and errors
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    toggled_count = 0
    skipped_count = 0
    errors = []

    for reward_id in body.reward_ids:
        try:
            reward = db.query(UserReward).filter(
                UserReward.id == reward_id,
                UserReward.event_id == event_id
            ).first()

            if not reward:
                errors.append(f"Reward {reward_id} not found")
                skipped_count += 1
                continue

            if not reward.manual_tracking_id:
                errors.append(f"Reward {reward_id} has no tracking data")
                skipped_count += 1
                continue

            # Update visibility and status
            reward.tracking_visible_to_user = body.visible

            if body.visible:
                reward.status = RewardStatus.TRACKING_ORDER
            else:
                reward.status = RewardStatus.READY_TO_SHIP

            toggled_count += 1

        except Exception as e:
            error_msg = f"Reward {reward_id}: {str(e)}"
            errors.append(error_msg)
            skipped_count += 1
            logger.error(f"❌ {error_msg}")

    db.commit()

    action = "shown" if body.visible else "hidden"
    logger.info(
        f"👁️  Bulk toggle: {toggled_count} rewards {action}, {skipped_count} skipped"
    )

    return ToggleVisibilityResponse(
        toggled_count=toggled_count,
        skipped_count=skipped_count,
        errors=errors
    )


@router.get("/events/{event_id}/rewards-with-tracking")
@limiter.limit(RateLimits.DEFAULT)
async def get_rewards_with_tracking(
    request: Request,
    response: Response,
    event_id: int,
    status_filter: Optional[str] = None,
    reward_type: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all rewards with tracking status for admin dashboard

    Returns list of rewards with shipping and tracking details for admin management.

    Args:
        event_id: Event ID
        status_filter: Filter by status (optional)
        reward_type: Filter by reward type (optional)
        page: Page number (default: 1)
        limit: Items per page (default: 50)
        current_user: Authenticated admin user
        db: Database session

    Returns:
        List of rewards with tracking status
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # Build query
    query = db.query(UserReward).filter(
        UserReward.event_id == event_id,
        UserReward.requires_shipping == True
    )

    if status_filter:
        try:
            reward_status = RewardStatus(status_filter)
            query = query.filter(UserReward.status == reward_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter: {status_filter}"
            )

    if reward_type:
        query = query.filter(UserReward.reward_type == reward_type)

    # Get total count
    total_count = query.count()

    # Paginate
    offset = (page - 1) * limit
    rewards = query.order_by(UserReward.created_at.desc()).offset(offset).limit(limit).all()

    # Build response
    rewards_data = []
    for reward in rewards:
        shipping = reward.shipping_details or {}
        user = reward.user

        rewards_data.append({
            "id": str(reward.id),
            "user_id": reward.user_id,
            "user_email": user.email if user else None,
            "user_name": user.full_name if user else None,
            "reward_name": reward.reward_name,
            "reward_type": reward.reward_type.value,
            "status": reward.status.value,
            "shipping_city": shipping.get("city"),
            "shipping_state": shipping.get("state"),
            "shipping_pincode": shipping.get("postal_code") or shipping.get("pincode"),
            "manual_tracking_id": reward.manual_tracking_id,
            "manual_tracking_url": reward.manual_tracking_url,
            "manual_courier_name": reward.manual_courier_name,
            "manual_order_reference": reward.manual_order_reference,
            "tracking_visible_to_user": reward.tracking_visible_to_user,
            "created_at": reward.created_at.isoformat(),
            "tracking_imported_at": reward.tracking_imported_at.isoformat() if reward.tracking_imported_at else None
        })

    return {
        "rewards": rewards_data,
        "total": total_count,
        "page": page,
        "limit": limit,
        "pages": (total_count + limit - 1) // limit
    }


@router.get("/{reward_id}/preview-tracking", response_model=TrackingPreviewResponse)
@limiter.limit(RateLimits.DEFAULT)
async def preview_tracking(
    request: Request,
    response: Response,
    reward_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Preview tracking details (admin only)

    Returns tracking information for admin verification.
    Doesn't require tracking_visible_to_user = True.

    Args:
        reward_id: Reward ID
        current_user: Authenticated admin user
        db: Database session

    Returns:
        TrackingPreviewResponse with tracking details
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    reward = db.query(UserReward).filter(UserReward.id == reward_id).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    return TrackingPreviewResponse(
        reward_id=reward.id,
        reward_name=reward.reward_name,
        tracking_id=reward.manual_tracking_id,
        tracking_url=reward.manual_tracking_url,
        courier_name=reward.manual_courier_name,
        order_reference=reward.manual_order_reference,
        status=reward.status.value,
        tracking_visible_to_user=reward.tracking_visible_to_user
    )


@router.patch("/{reward_id}/update-tracking")
@limiter.limit(RateLimits.DEFAULT)
async def update_tracking_info(
    request: Request,
    response: Response,
    reward_id: UUID,
    body: UpdateTrackingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Manually update tracking info for a reward

    Allows admin to correct or update tracking information without re-importing Excel.

    Args:
        reward_id: Reward ID
        body: Updated tracking information
        current_user: Authenticated admin user
        db: Database session

    Returns:
        Success response
    """
    # Check admin permission
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    reward = db.query(UserReward).filter(UserReward.id == reward_id).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    # Update tracking fields
    reward.manual_tracking_id = body.tracking_id
    reward.manual_tracking_url = body.tracking_url
    reward.manual_courier_name = body.courier_name
    reward.status = RewardStatus.TRACKING_ORDER
    reward.tracking_visible_to_user = True
    reward.tracking_imported_at = func.now()
    reward.tracking_imported_by_admin_id = current_user.id

    db.commit()

    logger.info(
        f"✏️  Admin {current_user.email} updated tracking for reward {reward_id}"
    )

    return {
        "success": True,
        "reward_id": str(reward_id),
        "message": "Tracking information updated successfully"
    }
