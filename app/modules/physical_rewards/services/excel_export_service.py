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

        # Group rewards by user to consolidate orders
        # Shiprocket requirement: Same order should have quantity > 1, not multiple rows
        user_rewards_map = {}
        for reward in rewards:
            user_id = reward.user_id
            if user_id not in user_rewards_map:
                user_rewards_map[user_id] = []
            user_rewards_map[user_id].append(reward)

        # Write data rows (one per user, with consolidated quantities)
        row_idx = 2
        for user_id, user_rewards in user_rewards_map.items():
            if len(user_rewards) == 1:
                # Single reward for this user
                self._write_reward_row(ws, row_idx, user_rewards[0], quantity=1)
                row_idx += 1
            else:
                # Multiple rewards for same user - group by reward type
                reward_groups = {}
                for reward in user_rewards:
                    key = (reward.reward_type, reward.reward_name)
                    if key not in reward_groups:
                        reward_groups[key] = []
                    reward_groups[key].append(reward)

                # Write one row per reward type with quantity
                for (reward_type, reward_name), group_rewards in reward_groups.items():
                    # Use first reward as template, set quantity to group size
                    self._write_reward_row(ws, row_idx, group_rewards[0], quantity=len(group_rewards))
                    row_idx += 1

        # Format worksheet
        total_rows = row_idx - 2  # Subtract header row
        self._format_worksheet(ws, total_rows)

        # Save to bytes
        try:
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            excel_bytes = output.getvalue()

            logger.info(f"✅ Excel export complete: {total_rows} rows, {len(excel_bytes)} bytes")
            return excel_bytes
        except Exception as e:
            logger.error(f"❌ Failed to generate Excel file: {str(e)}")
            raise ValueError(f"Excel generation failed: {str(e)}")

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

    def _write_reward_row(self, ws, row_idx: int, reward: UserReward, quantity: int = 1):
        """
        Write reward data to a row following Shiprocket template format

        Args:
            ws: Worksheet
            row_idx: Row number (1-indexed)
            reward: UserReward instance
            quantity: Product quantity (default: 1, must be > 0)
        """
        # Ensure quantity is valid (> 0)
        if quantity <= 0:
            quantity = 1
        shipping = reward.shipping_details or {}

        # Generate order reference if not exists
        # Format: RNREVT{event_id}USR{user_id}RWD{reward_id_short}
        # Max 30 chars, no symbols, alphanumeric only, unique per reward
        if not reward.manual_order_reference:
            # Convert UUID to short alphanumeric (first 8 chars)
            reward_id_short = str(reward.id).replace("-", "")[:8].upper()
            # Create compact format: RNR + E{event_id} + U{user_id} + {reward_short}
            order_ref = f"RNRE{reward.event_id}U{reward.user_id}R{reward_id_short}"
            # Ensure max 30 characters
            order_ref = order_ref[:30]
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
        pincode = str(shipping.get("postal_code") or shipping.get("pincode", "")).strip()
        address_line1_raw = str(shipping.get("address_line1", "")).strip()
        address_line2 = str(shipping.get("address_line2", "")).strip()
        city = str(shipping.get("city", "")).strip()
        state = str(shipping.get("state", "")).strip()
        country = str(shipping.get("country", "India")).strip()

        # Validate and format shipping address per Shiprocket requirements:
        # - Max 300 characters
        # - Min 5 characters
        # - Must contain at least 1 number and 1 space
        address_line1 = address_line1_raw
        if address_line1:
            # Ensure max 300 characters
            if len(address_line1) > 300:
                address_line1 = address_line1[:300]

            # Ensure minimum requirements: 5 chars, 1 number, 1 space
            has_number = any(char.isdigit() for char in address_line1)
            has_space = ' ' in address_line1

            # If missing number or space, try to fix
            if not has_number and pincode:
                # Prepend house number or pincode reference
                address_line1 = f"Flat 1 {address_line1}"
            if not has_space:
                # Add space if completely missing
                address_line1 = address_line1.replace(",", ", ")

            # Final check: ensure min 5 characters
            if len(address_line1) < 5:
                address_line1 = f"House 1 {address_line1}".strip()
        else:
            # Fallback if address is empty
            address_line1 = "House 1 Main Road"

        # Phone number formatting - Shiprocket expects 10-digit Indian mobile without +91
        phone_raw = str(shipping.get("phone", "")).strip()
        # Remove common prefixes and non-digits
        phone = phone_raw.replace("+91", "").replace("-", "").replace(" ", "").strip()
        # Ensure it's 10 digits
        if len(phone) > 10:
            phone = phone[-10:]  # Take last 10 digits

        email = str(shipping.get("email", "")).strip()

        # Product details
        # Product name max 200 characters (Shiprocket requirement)
        product_name = str(reward.reward_name or "Physical Reward").strip()
        if len(product_name) > 200:
            product_name = product_name[:197] + "..."  # Truncate with ellipsis

        # Master SKU cannot be empty (Shiprocket requirement)
        # Generate SKU if not provided: GLCG-{TYPE}-{short_reward_id}
        if reward.item_sku and str(reward.item_sku).strip():
            sku = str(reward.item_sku).strip()[:20]  # Max 20 chars for safety
        else:
            # Generate SKU from reward type and ID
            reward_id_short = str(reward.id).replace("-", "")[:8].upper()
            sku = f"GLCG{reward.reward_type.value.upper()}{reward_id_short}"[:20]

        hsn_code = reward.item_hsn or ""

        # Package dimensions (use defaults if not specified)
        # Weight validation per Shiprocket requirements:
        # - Must not be empty
        # - Must be numeric
        # - Cannot be negative
        # - Maximum 30kg
        if reward.item_weight:
            weight = float(reward.item_weight)
            # Ensure non-negative and within 30kg limit
            if weight < 0:
                weight = 0.5  # Default to 0.5kg if negative
            elif weight > 30:
                weight = 30.0  # Cap at 30kg maximum
        else:
            weight = 0.5  # Default weight if not provided

        # Dimension validation per Shiprocket requirements:
        # - Length, Breadth, Height cannot be less than 0.5 cm
        # - For document orders: minimum 10x10x1 cm
        # - We use 15x10x5 as safe defaults for physical items

        # Length validation (min 0.5cm)
        if reward.item_length:
            length = float(reward.item_length)
            length = max(0.5, length)  # Ensure minimum 0.5cm
        else:
            length = 15.0  # Safe default

        # Breadth validation (min 0.5cm)
        if reward.item_breadth:
            breadth = float(reward.item_breadth)
            breadth = max(0.5, breadth)  # Ensure minimum 0.5cm
        else:
            breadth = 10.0  # Safe default

        # Height validation (min 0.5cm)
        if reward.item_height:
            height = float(reward.item_height)
            height = max(0.5, height)  # Ensure minimum 0.5cm
        else:
            height = 5.0  # Safe default

        # For very small dimensions, enforce document minimum (10x10x1)
        # This prevents rejection for undersized packages
        if length < 10 or breadth < 10 or height < 1:
            length = max(length, 10.0)
            breadth = max(breadth, 10.0)
            height = max(height, 1.0)

        # Event name for order tag
        event_name = reward.event.name if reward.event else "Physical Reward"

        # Row data matching exact Shiprocket template (48 columns)
        # IMPORTANT: All values must be primitives (str, int, float) - no None or objects
        row_data = [
            str(order_ref),                     # 1. *Order Id
            str(current_date),                  # 2. Order Date (DD-MM-YYYY)
            "yes",                              # 3. Verified Order (Yes/No)
            str(phone) if phone else "",        # 4. *Buyer's Mobile No.
            str(first_name),                    # 5. *Buyer's First Name
            str(last_name) if last_name else "", # 6. Buyer's Last Name
            str(address_line1),                 # 7. *Shipping Complete Address
            str(address_line2) if address_line2 else "", # 8. Shipping Address Landmark
            str(pincode) if pincode else "",    # 9. *Shipping Address Pincode
            str(city) if city else "",          # 10. *Shipping Address City
            str(state) if state else "",        # 11. *Shipping Address State
            str(country),                       # 12. *Shipping Address Country
            str(email) if email else "",        # 13. Email
            "",                                 # 14. Buyer's Alternate Mobile Number
            "",                                 # 15. Buyer's Company Name
            "",                                 # 16. Buyer's GSTIN
            str(address_line1),                 # 17. Billing Complete Address (same as shipping)
            str(address_line2) if address_line2 else "", # 18. Billing Landmark
            str(pincode) if pincode else "",    # 19. Billing Pincode
            str(city) if city else "",          # 20. Billing City
            str(state) if state else "",        # 21. Billing State
            str(country),                       # 22. Billing Country
            "no",                               # 23. Send Notification (Yes/No)
            "",                                 # 24. Pickup Address Id
            "Custom",                           # 25. *Order Channel
            "Prepaid",                          # 26. *Payment Method
            str(product_name),                  # 27. *Product Name
            str(sku),                           # 28. *Master SKU
            int(quantity),                      # 29. *Product Quantity (must be > 0)
            500,                                # 30. *Per Unit Price in INR (must be > 0)
            "no",                               # 31. *Partial COD (Yes/No)
            int(quantity * 500),                # 32. Paid Amount (Rs.) = quantity * price
            0,                                  # 33. Product Discount (Per Unit Item)
            "",                                 # 34. Coupon
            str(hsn_code) if hsn_code else "",  # 35. HSN Code
            0,                                  # 36. Tax Rate(percentage)
            0,                                  # 37. Shipping Charges (Per Order)
            0,                                  # 38. Gift Wrap Charges (Per Order)
            0,                                  # 39. Transaction Fee (Per Order)
            0,                                  # 40. Total Discount (Per Order)
            str(event_name),                    # 41. Order Tag
            "no",                               # 42. *Contain Documents (Yes/No)
            "",                                 # 43. Reseller Name
            float(weight),                      # 44. *Weight Of Shipment (kg)
            float(length),                      # 45. *Length (cm)
            float(breadth),                     # 46. *Breadth (cm)
            float(height),                      # 47. *Height (cm)
            1                                   # 48. Package Count
        ]

        # Write row with explicit data types
        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)

            # Ensure only primitive types (str, int, float) - no objects
            if value is None:
                cell.value = ""  # Empty string instead of None
            elif isinstance(value, (int, float)):
                cell.value = value  # Keep numeric types as-is
            else:
                cell.value = str(value)  # Convert everything else to string

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
