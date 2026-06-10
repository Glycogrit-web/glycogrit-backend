#!/usr/bin/env python3
"""
Extract column headers from Shiprocket Excel template
"""
import zipfile
import xml.etree.ElementTree as ET
import re
from collections import OrderedDict

def column_index_from_string(col):
    """Convert column letter to index (A=0, B=1, ..., Z=25, AA=26, etc.)"""
    result = 0
    for char in col:
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result - 1

# Extract shared strings
with zipfile.ZipFile('Bulk Order Advance Excel File.xlsx', 'r') as z:
    shared_strings_xml = z.read('xl/sharedStrings.xml')
    sheet_xml = z.read('xl/worksheets/sheet1.xml')

# Parse shared strings
root = ET.fromstring(shared_strings_xml)
strings = []
for si in root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'):
    if si.text:
        strings.append(si.text)

# Parse sheet
sheet_root = ET.fromstring(sheet_xml)
sheet_data = sheet_root.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData')

# Find row 2 (actual column headers)
row_2 = None
for row in sheet_data.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
    if row.get('r') == '2':
        row_2 = row
        break

if not row_2:
    print("ERROR: Row 2 not found!")
    exit(1)

# Extract headers
headers = OrderedDict()
for cell in row_2.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
    cell_ref = cell.get('r')
    col_match = re.match(r'([A-Z]+)\d+', cell_ref)
    if not col_match:
        continue

    col = col_match.group(1)
    col_idx = column_index_from_string(col)

    cell_type = cell.get('t')
    v_elem = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')

    value = ""
    if v_elem is not None:
        if cell_type == 's':  # Shared string
            idx = int(v_elem.text)
            if 0 <= idx < len(strings):
                value = strings[idx]
        else:
            value = v_elem.text

    if value and value.strip():
        headers[col_idx] = value

# Sort by column index and print
print("\n" + "="*80)
print("SHIPROCKET BULK ORDER TEMPLATE - COLUMN HEADERS")
print("="*80)

for i, (col_idx, header) in enumerate(sorted(headers.items()), 1):
    required = " [REQUIRED]" if header.startswith("*") else ""
    clean_header = header.replace("*", "").strip()
    print(f"{i:3d}. {clean_header:60s}{required}")

print(f"\nTotal columns: {len(headers)}")
print("\nRequired fields marked with *")
