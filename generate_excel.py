import openpyxl
from openpyxl.styles import Border, Side
import io
import base64

# Create a new workbook
workbook = openpyxl.Workbook()
sheet = workbook.active

# Add 4 blank lines (rows)
for _ in range(4):
    sheet.append([])

# Add a 5th line and apply underline border from A to G
thin_border = Border(bottom=Side(style='thin'))
for col_idx in range(1, 8): # Columns A to G
    cell = sheet.cell(row=5, column=col_idx)
    cell.border = thin_border

# Save the workbook to a BytesIO object
output = io.BytesIO()
workbook.save(output)
output.seek(0)

# Read the content as bytes
excel_content_bytes = output.read()

# Print the base64 encoded content
print(base64.b64encode(excel_content_bytes).decode('utf-8'))
