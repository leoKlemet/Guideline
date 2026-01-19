from reportlab.pdfgen import canvas
import os

pdf_dir = "apps/api/data/private"
os.makedirs(pdf_dir, exist_ok=True)
pdf_path = os.path.join(pdf_dir, "employee_handbook_march_2025.pdf")

c = canvas.Canvas(pdf_path)

# Page 1: Intro
c.drawString(100, 800, "Employee Handbook - March 2025")
c.drawString(100, 750, "Welcome to the company.")
c.showPage()

# Page 2: Table of Contents (should be skipped)
c.drawString(100, 800, "Table of Contents")
c.drawString(100, 750, "1. Introduction")
c.drawString(100, 730, "2. Benefits")
c.drawString(100, 710, "3. Work Hours")
c.showPage()

# Page 3: Sick Days
c.drawString(100, 800, "2. Benefits - Sick Days")
c.drawString(100, 750, "Employees receive 5 sick days (40 hours) per year.")
c.drawString(100, 730, "Unused sick time rolls over, capped at 64 hours.")
c.showPage()

# Page 4: Vacation
c.drawString(100, 800, "2. Benefits - Vacation")
c.drawString(100, 750, "Employees accrue up to 80 hours of vacation per year.")
c.drawString(100, 730, "There is no rollover for vacation days.")
c.showPage()

# Page 5: Work Hours
c.drawString(100, 800, "3. Work Hours")
c.drawString(100, 750, "The standard workweek is 40 hours.")
c.drawString(100, 730, "Core hours are Monday through Friday, 9am to 5pm.")
c.showPage()

c.save()
print(f"Generated {pdf_path}")
