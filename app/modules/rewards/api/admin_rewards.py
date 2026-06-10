"""
Admin Rewards API Endpoints
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.models.user import User
from app.modules.rewards.schemas.reward import (
    BulkShipmentUpdateResponse,
    ManualShipmentDetails,
    RewardResponse,
    RewardWithDetails,
    ShippingPreviewResponse,
    ShiprocketShipmentResponse,
    TrackingVisibilityRequest,
)
from app.modules.rewards.services.reward_service import RewardService

router = APIRouter(prefix="/admin/rewards", tags=["admin-rewards"])


@router.post(
    "/events/{event_id}/users/{user_id}/registrations/{registration_id}/unlock",
    response_model=RewardResponse,
    status_code=status.HTTP_201_CREATED,
)
def admin_unlock_reward(
    event_id: int,
    user_id: int,
    registration_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Admin unlocks a physical reward for a user.

    This creates a UserReward record in 'pending_details' status,
    allowing the user to claim it and provide shipping details.

    Business Rules:
    1. Admin only endpoint
    2. Registration must exist and match event_id/user_id
    3. One reward per registration
    4. Reward created in 'pending_details' status (user must provide shipping address)

    Process:
    - Creates UserReward record with status='pending_details'
    - User can then claim and provide shipping details
    - After shipping details provided, status changes to 'pending_shipment'
    """
    service = RewardService(db)

    reward = service.admin_unlock_reward(
        event_id=event_id,
        user_id=user_id,
        registration_id=registration_id,
    )

    return RewardResponse.model_validate(reward)


@router.get("/all", response_model=list[RewardWithDetails])
def get_all_rewards(
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Get all rewards for admin dashboard with filtering.

    Query parameters:
    - status_filter: Filter by reward status (pending_details, pending_shipment, shipped, delivered)
    - search: Search by user name, email, or tracking number

    Returns:
    - List of rewards with full details (user, event, registration, shipping, progress)
    """
    service = RewardService(db)
    rewards = service.get_all_rewards_with_details(
        status_filter=status_filter,
        search=search,
    )
    return rewards


@router.get("/{reward_id}/shipping-preview", response_model=ShippingPreviewResponse)
async def get_shipping_preview(
    reward_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Get shipping preview with estimated costs before creating order.

    Shows:
    - Package dimensions and weight
    - Shipping address and phone
    - Pickup location
    - Available couriers with rates and ETD
    - Serviceability status

    This allows admin to review all details before confirming shipment.
    """
    service = RewardService(db)
    preview = await service.get_shipping_preview(reward_id=reward_id)
    return preview


@router.post("/{reward_id}/ship-with-shiprocket", response_model=ShiprocketShipmentResponse)
async def ship_reward_with_shiprocket(
    reward_id: str,
    courier_id: Optional[int] = Query(None, description="Optional courier ID for manual selection"),
    selection_strategy: Optional[str] = Query(
        None,
        description="Optional strategy: cheapest, fastest, balanced",
        pattern="^(cheapest|fastest|balanced)$"
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Automatically create Shiprocket order and ship reward with auto-courier selection.

    Process:
    1. Validates reward exists and has shipping address
    2. Gets ShiprocketFulfillmentService
    3. Creates Shiprocket order with default dimensions (15x10x5, 0.5kg)
    4. Auto-selects courier (if enabled) or uses manual selection
    5. Assigns AWB tracking number
    6. Generates shipping label PDF
    7. Schedules pickup
    8. Updates reward status to 'shipped'

    Query Parameters:
    - courier_id: Optional courier company ID for manual selection (overrides auto-selection)
    - selection_strategy: Optional 'cheapest' | 'fastest' | 'balanced' (overrides config default)

    Returns:
    - Tracking details, label URL, courier info, cost savings
    """
    service = RewardService(db)
    result = await service.ship_reward_with_shiprocket(
        reward_id=reward_id,
        courier_id=courier_id,
        selection_strategy=selection_strategy
    )
    return result


@router.post("/{reward_id}/ship", response_model=RewardResponse)
def ship_reward_manually(
    reward_id: str,
    shipment_details: ManualShipmentDetails,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Mark reward as shipped with manually entered tracking details.

    Used when admin ships via external courier (not Shiprocket).

    Body:
    - tracking_number: Tracking/AWB number
    - courier_partner: Name of courier company
    - shipped_at: Optional timestamp (defaults to now)

    Returns:
    - Updated reward details
    """
    service = RewardService(db)
    reward = service.ship_reward_manually(
        reward_id=reward_id,
        tracking_number=shipment_details.tracking_number,
        courier_partner=shipment_details.courier_partner,
        shipped_at=shipment_details.shipped_at,
    )
    return RewardResponse.model_validate(reward)


@router.post("/{reward_id}/mark-delivered", response_model=RewardResponse)
def mark_reward_delivered(
    reward_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Manually mark reward as delivered.

    Used for manual confirmation when Shiprocket webhook doesn't update
    or for non-Shiprocket shipments.

    Returns:
    - Updated reward details with delivered status
    """
    service = RewardService(db)
    reward = service.mark_reward_delivered(reward_id=reward_id)
    return RewardResponse.model_validate(reward)


@router.patch(
    "/{reward_id}/tracking-visibility",
    response_model=RewardResponse,
    status_code=status.HTTP_200_OK,
)
def toggle_reward_tracking_visibility(
    reward_id: str,
    request: TrackingVisibilityRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Toggle tracking visibility for a reward.

    Admin-only endpoint to control whether user can see tracking info.
    Tracking stays hidden by default after order creation. Admin must
    explicitly unlock it for users to see tracking details.

    Business Rules:
    - Admin only endpoint
    - Cannot show tracking if no tracking number exists yet
    - Admin can lock/unlock tracking at any time

    Args:
        reward_id: UUID of the reward
        request: TrackingVisibilityRequest with visible boolean

    Returns:
        Updated reward details

    Raises:
        404: Reward not found
        400: Invalid reward ID or trying to show tracking without tracking number
    """
    service = RewardService(db)

    try:
        reward = service.toggle_tracking_visibility(reward_id, request.visible)
        return RewardResponse.model_validate(reward)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle tracking visibility: {str(e)}",
        )


@router.get("/export-pending-shipments", status_code=status.HTTP_200_OK)
def export_pending_shipments_to_excel(
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Export all rewards pending shipment to Excel for Shiprocket bulk upload.

    This generates an Excel file with all rewards that are ready to ship
    (status = 'pending_shipment' and has shipping_details).

    Excel columns:
    - Internal ID: Our reward ID (for later matching)
    - Order ID: Unique order reference for Shiprocket
    - Full Name: Customer name
    - Address Line 1: Street address
    - Address Line 2: Apartment/suite
    - City: City name
    - State: State name
    - Pincode: Postal code
    - Phone: Phone number
    - Email: Email address
    - Product Name: Reward name
    - Product SKU: Item SKU
    - Weight (kg): Package weight
    - Length (cm): Package length
    - Breadth (cm): Package breadth
    - Height (cm): Package height
    - AWB Code: (Empty - to be filled by Shiprocket)
    - Tracking Number: (Empty - to be filled by Shiprocket)
    - Courier Name: (Empty - to be filled by Shiprocket)

    Query Parameters:
    - event_id: Optional filter by specific event

    Returns:
    - Excel file stream for download
    """
    service = RewardService(db)
    excel_file = service.export_pending_shipments_to_excel(event_id=event_id)

    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=pending_shipments.xlsx"}
    )


@router.post("/import-shipment-tracking", response_model=BulkShipmentUpdateResponse)
async def import_shipment_tracking_from_excel(
    file: UploadFile = File(..., description="Excel file with AWB/tracking data from Shiprocket"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Import tracking data from Shiprocket Excel export and update rewards.

    This accepts the Excel file you get back from Shiprocket after bulk upload,
    with AWB codes and tracking information filled in.

    Expected Excel columns (must contain at least):
    - Internal ID or Order ID: To match our rewards
    - AWB Code or Tracking Number: The AWB/tracking code
    - Courier Name or Courier Partner: Courier company name (optional)

    Process:
    1. Reads Excel file
    2. Matches rows to rewards using Internal ID or Order ID
    3. Updates tracking_number, courier_partner
    4. Updates status to 'shipped'
    5. Sets shipped_at timestamp

    Returns:
    - Summary with counts of successful/failed updates
    - List of any errors encountered

    Raises:
    - 400: Invalid file format or required columns missing
    - 500: Processing error
    """
    service = RewardService(db)

    try:
        result = await service.import_shipment_tracking_from_excel(file)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import tracking data: {str(e)}",
        )
