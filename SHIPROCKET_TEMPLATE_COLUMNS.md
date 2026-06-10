# Shiprocket Bulk Order Template - Complete Column List

## Column Headers (in order)

1. **\*Order Id** [REQUIRED]
2. **Order Date (DD-MM-YYYY)** (Optional)
3. **Verified Order (Yes/No)** (Optional)
4. **\*Buyer's Mobile No.** [REQUIRED]
5. **\*Buyer's First Name** [REQUIRED]
6. **Buyer's Last Name** (Optional)
7. **\*Shipping Complete Address** [REQUIRED]
8. **Shipping Address Landmark** (Optional)
9. **\*Shipping Address Pincode** [REQUIRED]
10. **\*Shipping Address City** [REQUIRED]
11. **\*Shipping Address State** [REQUIRED]
12. **\*Shipping Address Country** [REQUIRED]
13. **Email** (Optional)
14. **Buyer's Alternate Mobile Number** (Optional)
15. **Buyer's Company Name** (Optional)
16. **Buyer's GSTIN** (Optional)
17. **Billing Complete Address** (Optional)
18. **Billing Landmark** (Optional)
19. **Billing Pincode** (Optional)
20. **Billing City** (Optional)
21. **Billing State** (Optional)
22. **Billing Country** (Optional)
23. **Send Notification (Yes/No)** (Optional)
24. **Pickup Address Id** (Optional)
25. **\*Order Channel** [REQUIRED]
26. **\*Payment Method (COD/Prepaid)** [REQUIRED]
27. **\*Product Name** [REQUIRED]
28. **\*Master SKU** [REQUIRED]
29. **\*Product Quantity** [REQUIRED]
30. **\*Per Unit Price in INR (Inclusive of Tax)** [REQUIRED]
31. **\*Partial COD (Yes/No)** [REQUIRED]
32. **Paid Amount (Rs.)** (Optional)
33. **Product Discount (Per Unit Item)** (Optional)
34. **Coupon** (Optional)
35. **HSN Code** (Optional)
36. **Tax Rate(percentage)** (Optional)
37. **Shipping Charges (Per Order)** (Optional)
38. **Gift Wrap Charges (Per Order)** (Optional)
39. **Transaction Fee (Per Order)** (Optional)
40. **Total Discount (Per Order)** (Optional)
41. **Order Tag** (Optional)
42. **\*Contain Documents (Yes/No)** [REQUIRED]
43. **Reseller Name** (Optional)
44. **\*Weight Of Shipment (kg)** [REQUIRED]
45. **\*Length (cm)** [REQUIRED]
46. **\*Breadth (cm)** [REQUIRED]
47. **\*Height (cm)** [REQUIRED]
48. **Package Count** (Optional)

## Total: 48 columns

## Required Fields (18 total)
- Order Id
- Buyer's Mobile No.
- Buyer's First Name
- Shipping Complete Address
- Shipping Address Pincode
- Shipping Address City
- Shipping Address State
- Shipping Address Country
- Order Channel
- Payment Method (COD/Prepaid)
- Product Name
- Master SKU
- Product Quantity
- Per Unit Price in INR (Inclusive of Tax)
- Partial COD (Yes/No)
- Contain Documents (Yes/No)
- Weight Of Shipment (kg)
- Length (cm)
- Breadth (cm)
- Height (cm)

## Mapping from UserReward to Shiprocket Template

### Our Data → Shiprocket Column
- Generated Order Reference → *Order Id
- Current Date → Order Date (DD-MM-YYYY)
- "No" → Verified Order (Yes/No)
- shipping_details.phone → *Buyer's Mobile No.
- shipping_details.full_name (first part) → *Buyer's First Name
- shipping_details.full_name (last part) → Buyer's Last Name
- shipping_details.address_line1 → *Shipping Complete Address
- shipping_details.address_line2 → Shipping Address Landmark
- shipping_details.postal_code / pincode → *Shipping Address Pincode
- shipping_details.city → *Shipping Address City
- shipping_details.state → *Shipping Address State
- shipping_details.country (default: India) → *Shipping Address Country
- shipping_details.email → Email
- "" → Buyer's Alternate Mobile Number
- "" → Buyer's Company Name
- "" → Buyer's GSTIN
- (Same as shipping) → Billing Complete Address
- (Same as shipping) → Billing Landmark
- (Same as shipping) → Billing Pincode
- (Same as shipping) → Billing City
- (Same as shipping) → Billing State
- (Same as shipping) → Billing Country
- "No" → Send Notification (Yes/No)
- "" → Pickup Address Id
- "Custom" → *Order Channel
- "Prepaid" → *Payment Method (COD/Prepaid)
- reward_name → *Product Name
- item_sku (or generate) → *Master SKU
- "1" → *Product Quantity
- "0" → *Per Unit Price in INR (free reward)
- "No" → *Partial COD (Yes/No)
- "0" → Paid Amount (Rs.)
- "0" → Product Discount (Per Unit Item)
- "" → Coupon
- item_hsn → HSN Code
- "0" → Tax Rate(percentage)
- "0" → Shipping Charges (Per Order)
- "0" → Gift Wrap Charges (Per Order)
- "0" → Transaction Fee (Per Order)
- "0" → Total Discount (Per Order)
- event_name or "Physical Reward" → Order Tag
- "No" → *Contain Documents (Yes/No)
- "" → Reseller Name
- item_weight (or default) → *Weight Of Shipment (kg)
- item_length (or default) → *Length (cm)
- item_breadth (or default) → *Breadth (cm)
- item_height (or default) → *Height (cm)
- "1" → Package Count
