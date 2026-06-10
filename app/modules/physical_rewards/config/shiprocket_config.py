"""
Shiprocket Configuration for Physical Rewards
All Shiprocket-related constants and configuration for the 30-column BASIC template
"""


class ShiprocketConfig:
    """Shiprocket BASIC template configuration (30 columns)"""

    # Default values for required fields
    DEFAULTS = {
        "per_unit_price": 500,
        "payment_method": "Prepaid",
        "partial_cod": "no",
        "country": "India",
        "weight_kg": 0.5,
        "length_cm": 15.0,
        "breadth_cm": 10.0,
        "height_cm": 5.0,
        "min_dimension_cm": 0.5,
        "document_min_length": 10.0,
        "document_min_breadth": 10.0,
        "document_min_height": 1.0,
        "max_weight_kg": 30.0,
    }

    # Validation rules
    VALIDATION = {
        "order_id_max_length": 30,
        "address_min_length": 5,
        "address_max_length": 300,
        "product_name_max_length": 200,
        "phone_length": 10,
        "sku_max_length": 20,
    }

    # Section headers for Row 1 (30 columns) - matches template exactly
    SECTION_HEADERS = [
        None,                   # Col 1
        "Pickup Details",       # Col 2
        "Buyer's Details",      # Col 3
        None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,  # Cols 4-18 (15 None)
        "Order Details",        # Col 19
        None, None, None, None, None, None,  # Cols 20-25 (6 None)
        "Package Details",      # Col 26
        None, None, None,       # Cols 27-29 (3 None)
        "Courier Details"       # Col 30
    ]

    # Column headers for Row 2 (30 columns) - EXACT from template with (Optional) suffix
    COLUMN_HEADERS = [
        "*Order Id",                                        # 1
        "Pickup Address Id (Optional)",                    # 2
        "*Buyer's Mobile No.",                             # 3
        "*Buyer's First Name",                             # 4
        "Buyer's Last Name (Optional)",                    # 5
        "Email (Optional)",                                # 6
        "*Shipping Complete Address",                      # 7
        "Shipping Address Landmark (Optional)",            # 8
        "*Shipping Address Pincode",                       # 9
        "*Shipping Address City",                          # 10
        "*Shipping Address State",                         # 11
        "*Shipping Address Country",                       # 12
        "Billing Complete Address (Optional)",             # 13
        "Billing Landmark (Optional)",                     # 14
        "Billing Pincode (Optional)",                      # 15
        "Billing City (Optional)",                         # 16
        "Billing State (Optional)",                        # 17
        "Billing Country (Optional)",                      # 18
        "*Product Name",                                   # 19
        "*Per Unit Price in INR (Inclusive of Tax)",       # 20
        "*Product Quantity",                               # 21
        "*Master SKU",                                     # 22
        "*Payment Method (COD/Prepaid)",                   # 23
        "*Partial COD (Yes/No)",                           # 24
        "Paid Amount (Rs.)",                               # 25
        "*Weight Of Shipment (kg)",                        # 26
        "*Length (cm)",                                    # 27
        "*Breadth (cm)",                                   # 28
        "*Height (cm)",                                    # 29
        "Courier ID (Optional)"                            # 30
    ]

    # Column widths for Excel formatting (30-column BASIC template)
    COLUMN_WIDTHS = {
        1: 35,   # Order Id
        2: 20,   # Pickup Address Id
        3: 18,   # Phone
        4: 20,   # First Name
        5: 20,   # Last Name
        6: 30,   # Email
        7: 40,   # Shipping Address
        8: 25,   # Landmark
        9: 15,   # Pincode
        10: 20,  # City
        11: 20,  # State
        12: 15,  # Country
        19: 30,  # Product Name
        20: 18,  # Price
        21: 12,  # Quantity
        22: 25,  # SKU
        23: 15,  # Payment Method
    }

    @staticmethod
    def get_paid_amount(quantity: int) -> int:
        """
        Calculate paid amount based on quantity

        Args:
            quantity: Number of items

        Returns:
            Total paid amount (quantity * per_unit_price)
        """
        return quantity * ShiprocketConfig.DEFAULTS["per_unit_price"]

    @staticmethod
    def validate_order_id(order_id: str) -> str:
        """
        Validate and format order ID per Shiprocket requirements:
        - Max 30 characters
        - Alphanumeric only (no symbols)

        Args:
            order_id: Original order ID

        Returns:
            Validated and formatted order ID
        """
        # Remove non-alphanumeric characters
        clean_id = ''.join(c for c in order_id if c.isalnum())
        # Truncate to max length
        return clean_id[:ShiprocketConfig.VALIDATION["order_id_max_length"]]

    @staticmethod
    def validate_phone(phone: str) -> str:
        """
        Validate phone number per Shiprocket requirements:
        - 10 digits only
        - No +91 prefix

        Args:
            phone: Original phone number

        Returns:
            Validated 10-digit phone number
        """
        # Remove all non-digit characters
        clean_phone = ''.join(c for c in phone if c.isdigit())
        # Take last 10 digits if longer
        if len(clean_phone) > 10:
            clean_phone = clean_phone[-10:]
        return clean_phone

    @staticmethod
    def validate_address(address: str, pincode: str = "") -> str:
        """
        Validate shipping address per Shiprocket requirements:
        - Max 300 characters
        - Min 5 characters
        - Must contain at least 1 number and 1 space

        Args:
            address: Original address
            pincode: Postal code (used to auto-fix if address lacks number)

        Returns:
            Validated and formatted address
        """
        if not address:
            return "House 1 Main Road"

        # Ensure max length
        if len(address) > ShiprocketConfig.VALIDATION["address_max_length"]:
            address = address[:ShiprocketConfig.VALIDATION["address_max_length"]]

        # Ensure minimum requirements: 5 chars, 1 number, 1 space
        has_number = any(c.isdigit() for c in address)
        has_space = ' ' in address

        # Auto-fix: add house number if missing
        if not has_number and pincode:
            address = f"Flat 1 {address}"

        # Auto-fix: add space by replacing commas
        if not has_space:
            address = address.replace(",", ", ")

        # Ensure minimum length
        if len(address) < ShiprocketConfig.VALIDATION["address_min_length"]:
            address = f"House 1 {address}".strip()

        return address

    @staticmethod
    def validate_product_name(product_name: str) -> str:
        """
        Validate product name per Shiprocket requirements:
        - Max 200 characters

        Args:
            product_name: Original product name

        Returns:
            Validated product name (truncated with ellipsis if needed)
        """
        if len(product_name) > ShiprocketConfig.VALIDATION["product_name_max_length"]:
            return product_name[:197] + "..."
        return product_name

    @staticmethod
    def validate_dimensions(
        weight: float,
        length: float,
        breadth: float,
        height: float
    ) -> tuple:
        """
        Validate package dimensions per Shiprocket requirements:
        - Weight: 0-30kg (positive, non-zero)
        - Length/Breadth: min 0.5cm
        - Height: min 0.5cm
        - Document minimum: 10x10x1cm

        Args:
            weight: Package weight in kg
            length: Package length in cm
            breadth: Package breadth in cm
            height: Package height in cm

        Returns:
            Tuple of validated (weight, length, breadth, height)
        """
        # Weight validation (0-30kg)
        if weight <= 0:
            weight = ShiprocketConfig.DEFAULTS["weight_kg"]
        elif weight > ShiprocketConfig.DEFAULTS["max_weight_kg"]:
            weight = ShiprocketConfig.DEFAULTS["max_weight_kg"]

        # Dimension minimums (0.5cm each)
        min_dim = ShiprocketConfig.DEFAULTS["min_dimension_cm"]
        length = max(length, min_dim) if length > 0 else ShiprocketConfig.DEFAULTS["length_cm"]
        breadth = max(breadth, min_dim) if breadth > 0 else ShiprocketConfig.DEFAULTS["breadth_cm"]
        height = max(height, min_dim) if height > 0 else ShiprocketConfig.DEFAULTS["height_cm"]

        # Document minimum enforcement (10x10x1cm)
        # If dimensions are too small, enforce document minimums
        if length < ShiprocketConfig.DEFAULTS["document_min_length"] or \
           breadth < ShiprocketConfig.DEFAULTS["document_min_breadth"] or \
           height < ShiprocketConfig.DEFAULTS["document_min_height"]:
            length = max(length, ShiprocketConfig.DEFAULTS["document_min_length"])
            breadth = max(breadth, ShiprocketConfig.DEFAULTS["document_min_breadth"])
            height = max(height, ShiprocketConfig.DEFAULTS["document_min_height"])

        return weight, length, breadth, height

    @staticmethod
    def generate_sku(reward_id: str, reward_type: str) -> str:
        """
        Generate SKU for reward if not provided
        Format: GLCG{TYPE}{SHORT_ID}

        Args:
            reward_id: UUID of the reward
            reward_type: Type of reward (medal, tshirt, etc.)

        Returns:
            Generated SKU (max 20 characters)
        """
        # Convert UUID to short alphanumeric (first 8 chars)
        reward_id_short = str(reward_id).replace("-", "")[:8].upper()
        # Create SKU: GLCG + TYPE + SHORT_ID
        sku = f"GLCG{reward_type.upper()}{reward_id_short}"
        # Truncate to max length
        return sku[:ShiprocketConfig.VALIDATION["sku_max_length"]]
