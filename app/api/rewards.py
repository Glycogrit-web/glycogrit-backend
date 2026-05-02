"""
Rewards API Endpoints
Handles reward tracking, claiming, shipping with Shiprocket integration
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request, Header
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from app.core.database import get_db
from app.core.auth import get_current_user, require_admin
from app.models.user import User
from app.models.event import Event
from app.models.user_reward import UserReward, RewardStatus, RewardType
from app.models.shiprocket_order import ShiprocketOrder
from app.services.shiprocket import RewardFulfillmentService
from app.services.shiprocket.webhook_service import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


# ============================================================================
# Pydantic Schemas (Response Models)
# ============================================================================

from pydantic import BaseModel, Field


class ShippingDetailsRequest(BaseModel):
    """Shipping address for reward delivery"""
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    address_line1: str = Field(..., min_length=5, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=4, max_length=10)
    country: str = Field(default="India", max_length=100)
    email: Optional[str] = Field(None, max_length=255)


class RewardResponse(BaseModel):
    """Single reward response"""
    id: str
    user_id: int
    event_id: int
    reward_type: str
    reward_name: str
    status: str
    requires_shipping: bool
    shipping_details: Optional[dict]
    tracking_number: Optional[str]
    tracking_url: Optional[str]
    courier_partner: Optional[str]
    estimated_delivery_date: Optional[str]
    actual_delivery_date: Optional[str]
    current_location: Optional[str]
    status_history: Optional[List[dict]]
    created_at: datetime
    claimed_at: Optional[datetime]
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]

    class Config:
        from_attributes = True


class RewardListResponse(BaseModel):
    """List of rewards"""
    rewards: List[RewardResponse]
    total: int


class BulkShipRequest(BaseModel):
    """Request to ship multiple rewards"""
    reward_ids: List[str] = Field(..., min_items=1)


class BulkShipResponse(BaseModel):
    """Response for bulk shipment"""
    success_count: int
    failed_count: int
    results: List[dict]
    failed_orders: List[dict]


# ============================================================================
# User Endpoints - Claim Rewards & Track Shipments
# ============================================================================

@router.get("/me", response_model=RewardListResponse)
async def get_my_rewards(
    status: Optional[str] = Query(None, description="Filter by status"),
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all rewards earned by the current user.

    Query parameters:
    - status: Filter by reward status (pending_details, pending_shipment, shipped, etc.)
    - event_id: Filter by specific event

    Returns list of rewards with tracking information.
    """
    query = db.query(UserReward).filter(UserReward.user_id == current_user.id)

    if status:
        try:
            reward_status = RewardStatus(status)
            query = query.filter(UserReward.status == reward_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )

    if event_id:
        query = query.filter(UserReward.event_id == event_id)

    rewards = query.order_by(UserReward.created_at.desc()).all()

    return RewardListResponse(
        rewards=[RewardResponse.from_orm(r) for r in rewards],
        total=len(rewards)
    )


@router.get("/{reward_id}", response_model=RewardResponse)
async def get_reward_details(
    reward_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific reward.

    Includes tracking details, status history, and shipment information.
    """
    reward = db.query(UserReward).filter(
        UserReward.id == reward_id,
        UserReward.user_id == current_user.id
    ).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    return RewardResponse.from_orm(reward)


@router.post("/{reward_id}/claim", response_model=RewardResponse)
async def claim_reward(
    reward_id: str,
    shipping_details: ShippingDetailsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Claim a reward by providing shipping address.

    After claiming, reward moves to 'pending_shipment' status
    and admin can create Shiprocket order.

    Body:
    - full_name: Recipient name
    - phone: Contact number
    - address_line1: Street address
    - address_line2: Apartment/Suite (optional)
    - city: City
    - state: State
    - postal_code: PIN code
    - country: Country (default: India)
    - email: Email for tracking updates (optional)
    """
    # Get reward
    reward = db.query(UserReward).filter(
        UserReward.id == reward_id,
        UserReward.user_id == current_user.id
    ).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    # Check if reward requires shipping
    if not reward.requires_shipping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reward doesn't require shipping"
        )

    # Check current status
    if reward.status != RewardStatus.PENDING_DETAILS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reward already claimed. Current status: {reward.status.value}"
        )

    # Update shipping details
    reward.shipping_details = shipping_details.dict()
    reward.status = RewardStatus.PENDING_SHIPMENT
    reward.claimed_at = func.now()

    # Add to status history
    if not reward.status_history:
        reward.status_history = []

    reward.status_history.append({
        "status": RewardStatus.PENDING_SHIPMENT.value,
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Shipping address provided by user"
    })

    db.commit()
    db.refresh(reward)

    logger.info(f"✅ Reward {reward_id} claimed by user {current_user.id}")

    return RewardResponse.from_orm(reward)


@router.get("/{reward_id}/tracking", response_model=RewardResponse)
async def track_reward(
    reward_id: str,
    refresh: bool = Query(False, description="Refresh from Shiprocket"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get tracking information for a reward.

    Query parameters:
    - refresh: If true, fetches latest status from Shiprocket API

    Returns reward with current location, status, and tracking URL.
    """
    reward = db.query(UserReward).filter(
        UserReward.id == reward_id,
        UserReward.user_id == current_user.id
    ).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    # Refresh tracking if requested and reward has been shipped
    if refresh and reward.shiprocket_shipment_id:
        service = RewardFulfillmentService(db)
        try:
            result = await service.refresh_tracking(reward_id)
            if result["success"]:
                db.refresh(reward)
                logger.info(f"✅ Tracking refreshed for reward {reward_id}")
        except Exception as e:
            logger.error(f"❌ Failed to refresh tracking: {str(e)}")
            # Continue anyway and return current data

    return RewardResponse.from_orm(reward)


# ============================================================================
# Admin Endpoints - Manage Rewards & Shipments
# ============================================================================

@router.get("/admin/pending", response_model=RewardListResponse)
async def get_pending_shipments(
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all rewards pending shipment (Admin only).

    These are rewards where users have provided shipping address
    but Shiprocket order hasn't been created yet.

    Query parameters:
    - event_id: Filter by specific event
    """
    service = RewardFulfillmentService(db)
    rewards = service.get_pending_shipment_rewards(event_id)

    return RewardListResponse(
        rewards=[RewardResponse.from_orm(r) for r in rewards],
        total=len(rewards)
    )


@router.get("/admin/shipped", response_model=RewardListResponse)
async def get_shipped_rewards(
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all shipped rewards (Admin only).

    Includes rewards that are shipped, in transit, or out for delivery.

    Query parameters:
    - event_id: Filter by specific event
    """
    service = RewardFulfillmentService(db)
    rewards = service.get_shipped_rewards(event_id)

    return RewardListResponse(
        rewards=[RewardResponse.from_orm(r) for r in rewards],
        total=len(rewards)
    )


@router.post("/admin/{reward_id}/ship")
async def create_shipment(
    reward_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create Shiprocket order for a single reward (Admin only).

    This will:
    1. Create order in Shiprocket
    2. Auto-generate shipping label (if configured)
    3. Auto-schedule pickup (if configured)

    Returns order details including tracking number and label URL.
    """
    service = RewardFulfillmentService(db)

    try:
        result = await service.create_shiprocket_order(reward_id)

        if result["success"]:
            logger.info(f"✅ Shipment created for reward {reward_id}")
            return {
                "success": True,
                "message": "Shipment created successfully",
                "reward_id": result["reward_id"],
                "shiprocket_order_id": result["shiprocket_order_id"],
                "shiprocket_shipment_id": result["shiprocket_shipment_id"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

    except Exception as e:
        logger.error(f"❌ Failed to create shipment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create shipment: {str(e)}"
        )


@router.post("/admin/bulk-ship", response_model=BulkShipResponse)
async def bulk_ship_rewards(
    request: BulkShipRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create Shiprocket orders for multiple rewards (Admin only).

    Body:
    - reward_ids: Array of reward UUIDs

    Returns summary of successful and failed shipments.
    """
    service = RewardFulfillmentService(db)

    try:
        result = await service.bulk_create_orders(request.reward_ids)

        logger.info(
            f"✅ Bulk shipment: {result['success_count']} succeeded, "
            f"{result['failed_count']} failed"
        )

        return BulkShipResponse(**result)

    except Exception as e:
        logger.error(f"❌ Bulk shipment failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk shipment failed: {str(e)}"
        )


@router.post("/admin/{reward_id}/refresh-tracking")
async def refresh_tracking(
    reward_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Manually refresh tracking status from Shiprocket (Admin only).

    Fetches latest shipment status and updates reward accordingly.
    """
    service = RewardFulfillmentService(db)

    try:
        result = await service.refresh_tracking(reward_id)

        if result["success"]:
            logger.info(f"✅ Tracking refreshed for reward {reward_id}")
            return {
                "success": True,
                "message": "Tracking updated successfully",
                "reward": RewardResponse.from_orm(result["reward"])
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

    except Exception as e:
        logger.error(f"❌ Failed to refresh tracking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh tracking: {str(e)}"
        )


@router.get("/admin/{reward_id}/label")
async def get_shipping_label(
    reward_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get shipping label URL for a reward (Admin only).

    Returns the Shiprocket label PDF URL for printing.
    """
    reward = db.query(UserReward).filter(UserReward.id == reward_id).first()

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reward not found"
        )

    shiprocket_order = reward.shiprocket_order

    if not shiprocket_order or not shiprocket_order.label_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipping label not generated yet"
        )

    return {
        "reward_id": str(reward.id),
        "label_url": shiprocket_order.label_url,
        "manifest_url": shiprocket_order.manifest_url,
        "awb": shiprocket_order.shiprocket_awb
    }


# ============================================================================
# Stats & Analytics Endpoints (Admin)
# ============================================================================

@router.get("/admin/stats")
async def get_reward_stats(
    event_id: Optional[int] = Query(None, description="Filter by event ID"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get reward fulfillment statistics (Admin only).

    Returns counts by status, shipping stats, etc.
    """
    query = db.query(
        UserReward.status,
        func.count(UserReward.id).label('count')
    )

    if event_id:
        query = query.filter(UserReward.event_id == event_id)

    stats_by_status = query.filter(
        UserReward.requires_shipping == True
    ).group_by(UserReward.status).all()

    total_rewards = db.query(func.count(UserReward.id)).filter(
        UserReward.requires_shipping == True
    )
    if event_id:
        total_rewards = total_rewards.filter(UserReward.event_id == event_id)
    total_rewards = total_rewards.scalar()

    return {
        "total_rewards": total_rewards,
        "by_status": {stat[0].value: stat[1] for stat in stats_by_status},
        "event_id": event_id
    }


# ============================================================================
# Webhook Endpoint (Shiprocket Integration)
# ============================================================================

@router.post("/webhooks/shiprocket", include_in_schema=False)
async def shiprocket_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    anx_api_key: Optional[str] = Header(None, alias="anx-api-key"),
    db: Session = Depends(get_db)
):
    """
    Receive real-time status updates from Shiprocket webhooks.

    Official Shiprocket Webhook Specifications:
    - Method: POST
    - Content-Type: application/json
    - Security Header: anx-api-key
    - Response: Must return 200 OK immediately
    - No keywords: shiprocket, kartrocket, sr, kr in webhook URL

    This endpoint processes shipment tracking updates in real-time,
    eliminating the need for manual tracking refresh.

    Example webhook payload:
    {
        "awb": "19041424751540",
        "courier_name": "Delhivery Surface",
        "current_status": "IN TRANSIT",
        "current_status_id": 20,
        "shipment_status": "IN TRANSIT",
        "shipment_status_id": 18,
        "current_timestamp": "23 05 2023 11:43:52",
        "order_id": "1373900_150876814",
        "sr_order_id": 348456385,
        "scans": [...]
    }

    Note: This endpoint is not shown in Swagger UI (include_in_schema=False)
    as it's meant for Shiprocket's internal use only.
    """
    try:
        # Parse webhook data
        webhook_data = await request.json()

        logger.info(f"📥 Received Shiprocket webhook for AWB: {webhook_data.get('awb')}")

        # Initialize webhook service
        # TODO: Get webhook secret from shiprocket_config table
        webhook_service = WebhookService(db, webhook_secret=None)

        # Verify signature if security token is provided
        if anx_api_key:
            is_valid = webhook_service.verify_signature(webhook_data, anx_api_key)
            if not is_valid:
                logger.warning("⚠️ Invalid webhook signature")
                # Still return 200 to prevent Shiprocket from retrying
                return {"status": "error", "message": "Invalid signature"}

        # Process webhook in background to return 200 immediately
        background_tasks.add_task(
            _process_webhook_background,
            webhook_data,
            db
        )

        # Return 200 OK immediately (required by Shiprocket)
        return {"status": "success", "message": "Webhook received"}

    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}")
        # Still return 200 to prevent Shiprocket from retrying failed webhooks
        return {"status": "error", "message": str(e)}


async def _process_webhook_background(webhook_data: dict, db: Session):
    """
    Process webhook data in background task.

    Args:
        webhook_data: Webhook payload from Shiprocket
        db: Database session
    """
    try:
        webhook_service = WebhookService(db)
        result = await webhook_service.process_webhook(webhook_data)

        if result["success"]:
            logger.info(f"✅ Webhook processed successfully: {result}")

            # TODO: Send user notification if status changed
            # if webhook_service.should_notify_user(old_status, new_status):
            #     await send_notification(user_id, status_change_message)

            # TODO: Alert admin if problematic status
            # if webhook_service.should_alert_admin(status, status_code):
            #     await alert_admin(reward_id, issue_description)
        else:
            logger.error(f"❌ Webhook processing failed: {result['error']}")

    except Exception as e:
        logger.error(f"❌ Background webhook processing error: {str(e)}")
        db.rollback()
