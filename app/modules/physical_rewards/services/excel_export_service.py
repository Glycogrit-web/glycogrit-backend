"""
Excel Export Service for Physical Rewards
Generates Shiprocket bulk order Excel files with exact 30-column BASIC template format
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
from app.modules.physical_rewards.config import ShiprocketConfig

logger = logging.getLogger(__name__)


class ExcelExportService:
    """Service for exporting physical reward shipping details to Shiprocket BASIC Excel format (30 columns)"""

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
        Export shipping details for rewards to Shiprocket BASIC Excel format (30 columns)

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
        # Data starts from row 3 (row 1 = section headers, row 2 = column headers)
        row_idx = 3
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
        total_rows = row_idx - 3  # Subtract header rows (2 rows)
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
        """Write section headers (row 1) and column headers (row 2) to worksheet"""
        section_font = Font(bold=True, size=12, color="FFFFFF")
        section_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        section_alignment = Alignment(horizontal="center", vertical="center")

        header_font = Font(bold=True, size=10)
        header_fill = PatternFill(start_color="B4C7E7", end_color="B4C7E7", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # Row 1: Section headers (merged cells for sections)
        for col_idx, section in enumerate(ShiprocketConfig.SECTION_HEADERS, start=1):
            cell = ws.cell(row=1, column=col_idx, value=section)
            if section:  # Only format cells with section headers
                cell.font = section_font
                cell.fill = section_fill
                cell.alignment = section_alignment

        # Row 2: Column headers
        for col_idx, header in enumerate(ShiprocketConfig.COLUMN_HEADERS, start=1):
            cell = ws.cell(row=2, column=col_idx, value=header)
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

        # Generate order reference if not exists - validate using ShiprocketConfig
        if not reward.manual_order_reference:
            # Convert UUID to short alphanumeric (first 8 chars)
            reward_id_short = str(reward.id).replace("-", "")[:8].upper()
            # Create compact format: RNR + E{event_id} + U{user_id} + {reward_short}
            order_ref_raw = f"RNRE{reward.event_id}U{reward.user_id}R{reward_id_short}"
            # Validate using ShiprocketConfig (ensures alphanumeric and max 30 chars)
            order_ref = ShiprocketConfig.validate_order_id(order_ref_raw)
        else:
            order_ref = ShiprocketConfig.validate_order_id(reward.manual_order_reference)

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

        # Validate and format shipping address using ShiprocketConfig
        address_line1 = ShiprocketConfig.validate_address(address_line1_raw, pincode)

        # Phone number formatting using ShiprocketConfig
        phone_raw = str(shipping.get("phone", "")).strip()
        phone = ShiprocketConfig.validate_phone(phone_raw)

        email = str(shipping.get("email", "")).strip()

        # Product details - validate product name using ShiprocketConfig
        product_name = str(reward.reward_name or "Physical Reward").strip()
        product_name = ShiprocketConfig.validate_product_name(product_name)

        # Master SKU cannot be empty - use existing or generate using ShiprocketConfig
        if reward.item_sku and str(reward.item_sku).strip():
            sku = str(reward.item_sku).strip()[:ShiprocketConfig.VALIDATION["sku_max_length"]]
        else:
            sku = ShiprocketConfig.generate_sku(reward.id, reward.reward_type.value)

        hsn_code = reward.item_hsn or ""

        # Package dimensions validation using ShiprocketConfig
        weight = float(reward.item_weight) if reward.item_weight else 0
        length = float(reward.item_length) if reward.item_length else 0
        breadth = float(reward.item_breadth) if reward.item_breadth else 0
        height = float(reward.item_height) if reward.item_height else 0

        # Validate all dimensions together
        weight, length, breadth, height = ShiprocketConfig.validate_dimensions(
            weight, length, breadth, height
        )

        # Row data matching exact Shiprocket BASIC template (30 columns)
        # IMPORTANT: All values must be primitives (str, int, float) - no None or objects
        # Using ShiprocketConfig.DEFAULTS for default values
        per_unit_price = ShiprocketConfig.DEFAULTS["per_unit_price"]
        paid_amount = ShiprocketConfig.get_paid_amount(quantity)

        row_data = [
            str(order_ref),                                     # 1. *Order Id
            "",                                                 # 2. Pickup Address Id (Optional)
            str(phone) if phone else "",                        # 3. *Buyer's Mobile No.
            str(first_name),                                    # 4. *Buyer's First Name
            str(last_name) if last_name else "",                # 5. Buyer's Last Name (Optional)
            str(email) if email else "",                        # 6. Email (Optional)
            str(address_line1),                                 # 7. *Shipping Complete Address
            str(address_line2) if address_line2 else "",        # 8. Shipping Address Landmark (Optional)
            str(pincode) if pincode else "",                    # 9. *Shipping Address Pincode
            str(city) if city else "",                          # 10. *Shipping Address City
            str(state) if state else "",                        # 11. *Shipping Address State
            str(country),                                       # 12. *Shipping Address Country
            str(address_line1),                                 # 13. Billing Complete Address (Optional, same as shipping)
            str(address_line2) if address_line2 else "",        # 14. Billing Landmark (Optional)
            str(pincode) if pincode else "",                    # 15. Billing Pincode (Optional)
            str(city) if city else "",                          # 16. Billing City (Optional)
            str(state) if state else "",                        # 17. Billing State (Optional)
            str(country),                                       # 18. Billing Country (Optional)
            str(product_name),                                  # 19. *Product Name
            per_unit_price,                                     # 20. *Per Unit Price in INR (from config)
            int(quantity),                                      # 21. *Product Quantity (must be > 0)
            str(sku),                                           # 22. *Master SKU
            ShiprocketConfig.DEFAULTS["payment_method"],       # 23. *Payment Method (from config)
            ShiprocketConfig.DEFAULTS["partial_cod"],          # 24. *Partial COD (from config)
            paid_amount,                                        # 25. Paid Amount (Rs.) = quantity * price
            float(weight),                                      # 26. *Weight Of Shipment (kg)
            float(length),                                      # 27. *Length (cm)
            float(breadth),                                     # 28. *Breadth (cm)
            float(height),                                      # 29. *Height (cm)
            ""                                                  # 30. Courier ID (Optional)
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
        # Set column widths from ShiprocketConfig
        for col_idx, width in ShiprocketConfig.COLUMN_WIDTHS.items():
            ws.column_dimensions[get_column_letter(col_idx)].width = width

        # Set default width for other columns
        for col_idx in range(1, len(ShiprocketConfig.COLUMN_HEADERS) + 1):
            if col_idx not in ShiprocketConfig.COLUMN_WIDTHS:
                ws.column_dimensions[get_column_letter(col_idx)].width = 15

        # Freeze header rows (rows 1-2)
        ws.freeze_panes = "A3"

        # Add auto-filter starting from row 2 (column headers)
        ws.auto_filter.ref = f"A2:{get_column_letter(len(ShiprocketConfig.COLUMN_HEADERS))}{num_rows + 2}"

        # Format pincode and phone as text (prevent Excel from treating as numbers)
        # Data starts from row 3
        for row_idx in range(3, num_rows + 3):
            # Pincode (column 9)
            ws.cell(row=row_idx, column=9).number_format = '@'
            # Phone (column 3)
            ws.cell(row=row_idx, column=3).number_format = '@'
