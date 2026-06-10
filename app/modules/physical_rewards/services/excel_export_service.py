"""
Excel Export Service for Physical Rewards
Generates Shiprocket bulk order Excel files with exact 48-column template format
"""
import io
import logging
from datetime import datetime
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.core.enums import RewardStatus, RewardType
from app.models.user_reward import UserReward

logger = logging.getLogger(__name__)


class ExcelExportService:
    """Service for exporting physical reward shipping details to Shiprocket Excel format"""

    # Shiprocket template column headers (EXACT - including asterisks for required fields)
    SHIPROCKET_COLUMNS = [
        "*Order Id",
        "Order Date (DD-MM-YYYY)",
        "Verified Order (Yes/No)",
        "*Buyer's Mobile No.",
        "*Buyer's First Name",
        "Buyer's Last Name",
        "*Shipping Complete Address",
        "Shipping Address Landmark",
        "*Shipping Address Pincode",
        "*Shipping Address City",
        "*Shipping Address State",
        "*Shipping Address Country",
        "Email",
        "Buyer's Alternate Mobile Number",
        "Buyer's Company Name",
        "Buyer's GSTIN",
        "Billing Complete Address",
        "Billing Landmark",
        "Billing Pincode",
        "Billing City",
        "Billing State",
        "Billing Country",
        "Send Notification (Yes/No)",
        "Pickup Address Id",
        "*Order Channel",
        "*Payment Method (COD/Prepaid)",
        "*Product Name",
        "*Master SKU",
        "*Product Quantity",
        "*Per Unit Price in INR (Inclusive of Tax)",
        "*Partial COD (Yes/No)",
        "Paid Amount (Rs.)",
        "Product Discount (Per Unit Item)",
        "Coupon",
        "HSN Code",
        "Tax Rate(percentage)",
        "Shipping Charges (Per Order)",
        "Gift Wrap Charges (Per Order)",
        "Transaction Fee (Per Order)",
        "Total Discount (Per Order)",
        "Order Tag",
        "*Contain Documents (Yes/No)",
        "Reseller Name",
        "*Weight Of Shipment (kg)",
        "*Length (cm)",
        "*Breadth (cm)",
        "*Height (cm)",
        "Package Count"
    ]

    def __init__(self, db: Session):
        """
        Initialize Excel export service

        Args:
            db: Database session
        """
        self.db = db

    def export_shipping_details(
        self,
        event_id: int,
        status: Optional[RewardStatus] = RewardStatus.READY_TO_SHIP,
        reward_type: Optional[str] = None
    ) -> bytes:
        """
        Export shipping details for rewards to Shiprocket Excel format (48 columns)

        Args:
            event_id: Event ID to export rewards for
            status: Filter by reward status (default: READY_TO_SHIP)
            reward_type: Optional filter by reward type (medal, tshirt, etc.)

        Returns:
            Excel file as bytes (XLSX format)

        Raises:
            ValueError: If no rewards found or required data missing
        """
        # Query rewards with shipping details
        query = self.db.query(UserReward).filter(
            UserReward.event_id == event_id,
            UserReward.requires_shipping == True,
            UserReward.shipping_details.isnot(None)
        )

        if status:
            query = query.filter(UserReward.status == status)

        if reward_type:
            query = query.filter(UserReward.reward_type == reward_type)

        rewards = query.all()

        if not rewards:
            logger.warning(f"No rewards found for event {event_id} with status {status}")

        logger.info(f"📊 Exporting {len(rewards)} rewards for event {event_id}")

        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Shiprocket Bulk Orders"

        # Write headers
        self._write_headers(ws)

        # Write data rows
        for idx, reward in enumerate(rewards, start=2):
            self._write_reward_row(ws, idx, reward)

        # Format worksheet
        self._format_worksheet(ws, len(rewards))

        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        logger.info(f"✅ Excel export complete: {len(rewards)} rows")
        return output.getvalue()

    def _write_headers(self, ws):
        """Write column headers to worksheet"""
        header_font = Font(bold=True, size=11)
        header_fill = PatternFill(start_color="CCE5FF", end_color="CCE5FF", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for col_idx, header in enumerate(self.SHIPROCKET_COLUMNS, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

    def _write_reward_row(self, ws, row_idx: int, reward: UserReward):
        """
        Write reward data to a row following Shiprocket template format

        Args:
            ws: Worksheet
            row_idx: Row number (1-indexed)
            reward: UserReward instance
        """
        shipping = reward.shipping_details or {}

        # Generate order reference if not exists
        if not reward.manual_order_reference:
            order_ref = f"RNR-EVT-{reward.event_id}-USR-{reward.user_id}-RWD-{str(reward.id)[:8].upper()}"
        else:
            order_ref = reward.manual_order_reference

        # Split name into first and last
        full_name = shipping.get("full_name") or shipping.get("name", "Customer")
        name_parts = full_name.strip().split(maxsplit=1)
        first_name = name_parts[0] if name_parts else "Customer"
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Current date in DD-MM-YYYY format
        current_date = datetime.now().strftime("%d-%m-%Y")

        # Get address fields (support both postal_code and pincode)
        pincode = shipping.get("postal_code") or shipping.get("pincode", "")
        address_line1 = shipping.get("address_line1", "")
        address_line2 = shipping.get("address_line2", "")
        city = shipping.get("city", "")
        state = shipping.get("state", "")
        country = shipping.get("country", "India")
        phone = shipping.get("phone", "")
        email = shipping.get("email", "")

        # Product details
        product_name = reward.reward_name
        sku = reward.item_sku or f"GLCG-{reward.reward_type.value.upper()}-{reward.id}"[:20]
        hsn_code = reward.item_hsn or ""

        # Package dimensions (use defaults if not specified)
        weight = float(reward.item_weight) if reward.item_weight else 0.5
        length = float(reward.item_length) if reward.item_length else 15.0
        breadth = float(reward.item_breadth) if reward.item_breadth else 10.0
        height = float(reward.item_height) if reward.item_height else 5.0

        # Event name for order tag
        event_name = reward.event.name if reward.event else "Physical Reward"

        # Row data matching exact Shiprocket template (48 columns)
        row_data = [
            order_ref,                          # 1. *Order Id
            current_date,                       # 2. Order Date (DD-MM-YYYY)
            "No",                               # 3. Verified Order (Yes/No)
            phone,                              # 4. *Buyer's Mobile No.
            first_name,                         # 5. *Buyer's First Name
            last_name,                          # 6. Buyer's Last Name
            address_line1,                      # 7. *Shipping Complete Address
            address_line2,                      # 8. Shipping Address Landmark
            pincode,                            # 9. *Shipping Address Pincode
            city,                               # 10. *Shipping Address City
            state,                              # 11. *Shipping Address State
            country,                            # 12. *Shipping Address Country
            email,                              # 13. Email
            "",                                 # 14. Buyer's Alternate Mobile Number
            "",                                 # 15. Buyer's Company Name
            "",                                 # 16. Buyer's GSTIN
            address_line1,                      # 17. Billing Complete Address (same as shipping)
            address_line2,                      # 18. Billing Landmark
            pincode,                            # 19. Billing Pincode
            city,                               # 20. Billing City
            state,                              # 21. Billing State
            country,                            # 22. Billing Country
            "No",                               # 23. Send Notification (Yes/No)
            "",                                 # 24. Pickup Address Id
            "Custom",                           # 25. *Order Channel
            "Prepaid",                          # 26. *Payment Method (free reward)
            product_name,                       # 27. *Product Name
            sku,                                # 28. *Master SKU
            "1",                                # 29. *Product Quantity
            "0",                                # 30. *Per Unit Price in INR (free reward)
            "No",                               # 31. *Partial COD (Yes/No)
            "0",                                # 32. Paid Amount (Rs.)
            "0",                                # 33. Product Discount (Per Unit Item)
            "",                                 # 34. Coupon
            hsn_code,                           # 35. HSN Code
            "0",                                # 36. Tax Rate(percentage)
            "0",                                # 37. Shipping Charges (Per Order)
            "0",                                # 38. Gift Wrap Charges (Per Order)
            "0",                                # 39. Transaction Fee (Per Order)
            "0",                                # 40. Total Discount (Per Order)
            event_name,                         # 41. Order Tag
            "No",                               # 42. *Contain Documents (Yes/No)
            "",                                 # 43. Reseller Name
            str(weight),                        # 44. *Weight Of Shipment (kg)
            str(length),                        # 45. *Length (cm)
            str(breadth),                       # 46. *Breadth (cm)
            str(height),                        # 47. *Height (cm)
            "1"                                 # 48. Package Count
        ]

        # Write row
        for col_idx, value in enumerate(row_data, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    def _format_worksheet(self, ws, num_rows: int):
        """
        Format worksheet for better readability

        Args:
            ws: Worksheet
            num_rows: Number of data rows
        """
        # Set column widths
        column_widths = {
            1: 35,   # Order Id
            2: 20,   # Order Date
            4: 18,   # Phone
            5: 20,   # First Name
            6: 20,   # Last Name
            7: 40,   # Shipping Address
            9: 15,   # Pincode
            10: 20,  # City
            11: 20,  # State
            13: 30,  # Email
            27: 30,  # Product Name
            28: 25,  # SKU
        }

        for col_idx, width in column_widths.items():
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        # Set default width for other columns
        for col_idx in range(1, len(self.SHIPROCKET_COLUMNS) + 1):
            if col_idx not in column_widths:
                ws.column_dimensions[get_column_letter(col_idx)].width = 15

        # Freeze header row
        ws.freeze_panes = "A2"

        # Add auto-filter
        ws.auto_filter.ref = f"A1:{get_column_letter(len(self.SHIPROCKET_COLUMNS))}{num_rows + 1}"

        # Format pincode and phone as text (prevent Excel from treating as numbers)
        for row_idx in range(2, num_rows + 2):
            # Pincode (column 9)
            ws.cell(row=row_idx, column=9).number_format = '@'
            # Phone (column 4)
            ws.cell(row=row_idx, column=4).number_format = '@'
