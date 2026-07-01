import os
import glob
import shutil
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def copy_images():
    print("Copying generated images from artifacts...")
    artifact_dir = r"C:\Users\seera\.gemini\antigravity-ide\brain\19a2e66e-51c6-469a-b4cd-928e82d6152e"
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)

    # Copy showroom sofa
    sofa_files = glob.glob(os.path.join(artifact_dir, "showroom_sofa*.png"))
    if sofa_files:
        latest_sofa = max(sofa_files, key=os.path.getctime)
        shutil.copy(latest_sofa, os.path.join(static_dir, "showroom_sofa.png"))
        print(f"Copied {latest_sofa} to static/showroom_sofa.png")
    else:
        print("Sofa image not found in artifacts!")

    # Copy engine diagram
    diagram_files = glob.glob(os.path.join(artifact_dir, "engine_diagram*.png"))
    if diagram_files:
        latest_diag = max(diagram_files, key=os.path.getctime)
        shutil.copy(latest_diag, os.path.join(static_dir, "engine_diagram.png"))
        print(f"Copied {latest_diag} to static/engine_diagram.png")
    else:
        print("Engine diagram not found in artifacts!")

def build_furniture_catalog():
    print("Generating luxury furniture catalog PDF...")
    pdf_path = os.path.join(os.path.dirname(__file__), "static", "luxury_furniture_catalog.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story = []

    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'CatalogTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#065f46'),  # Emerald Green
        alignment=1,  # Centered
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'CatalogSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#6b7280'),
        alignment=1,
        spaceAfter=30
    )
    
    section_style = ParagraphStyle(
        'CatalogSection',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=15,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'CatalogBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )

    story.append(Paragraph("KRID LUXURY HOME", title_style))
    story.append(Paragraph("Exquisite Handcrafted Furniture Collection — Autumn 2026 Catalog", subtitle_style))
    story.append(Spacer(1, 10))

    # Catalog Items Table
    data = [
        [
            Paragraph("<b>Category & Item</b>", body_style),
            Paragraph("<b>Description & Materials</b>", body_style),
            Paragraph("<b>Starting Price</b>", body_style)
        ],
        [
            Paragraph("<b>The Hampton Sectional</b><br/><i>Sofas</i>", body_style),
            Paragraph("Deep-seated premium linen sectional with high-density memory foam core and solid ashwood legs.", body_style),
            Paragraph("<b>$4,500</b>", body_style)
        ],
        [
            Paragraph("<b>The Verona Sofa</b><br/><i>Sofas</i>", body_style),
            Paragraph("Italian full-grain leather couch. Features sleek curved lines, low profile, and polished steel frames.", body_style),
            Paragraph("<b>$3,800</b>", body_style)
        ],
        [
            Paragraph("<b>The Royal Armchair</b><br/><i>Seating</i>", body_style),
            Paragraph("Classic wingback lounge chair upholstered in rich forest velvet with walnut-stained legs.", body_style),
            Paragraph("<b>$1,500</b>", body_style)
        ],
        [
            Paragraph("<b>The Carrara Dining Table</b><br/><i>Tables</i>", body_style),
            Paragraph("A stunning slab of honed white Carrara marble supported by a sculptural brass pedestal base.", body_style),
            Paragraph("<b>$3,200</b>", body_style)
        ],
        [
            Paragraph("<b>The Handcrafted Oak Table</b><br/><i>Tables</i>", body_style),
            Paragraph("Solid European oak table. Plank construction highlighting natural knots and organic edges.", body_style),
            Paragraph("<b>$2,800</b>", body_style)
        ]
    ]

    t = Table(data, colWidths=[130, 310, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f0fdfa')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0f766e')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#ffffff')),
    ]))
    
    story.append(t)
    story.append(Spacer(1, 30))
    
    footer_style = ParagraphStyle(
        'CatalogFooter',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#065f46'),
        alignment=1,
        spaceBefore=20
    )
    story.append(Paragraph("Custom sizes, layouts, and upholstery options are available.", footer_style))
    story.append(Paragraph("Schedule a private showroom concierge consultation by texting 'appointment' to our agent.", ParagraphStyle('CatF2', parent=footer_style, fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#475569'))))
    
    doc.build(story)
    print("Catalog PDF generated successfully!")

def build_invoice_pdf():
    print("Generating automotive service invoice PDF...")
    pdf_path = os.path.join(os.path.dirname(__file__), "static", "sample_invoice.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story = []

    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1d4ed8'),  # Royal Blue
        spaceAfter=5
    )
    
    meta_style = ParagraphStyle(
        'InvoiceMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569')
    )
    
    header_right = ParagraphStyle(
        'HeaderRight',
        parent=meta_style,
        alignment=2  # Right-aligned
    )

    # 1. Header Section Table
    header_data = [
        [
            Paragraph("AUTOMOTIVE CARE SHOP", title_style),
            Paragraph("<b>INVOICE / ESTIMATE</b>", ParagraphStyle('InvRight', parent=title_style, alignment=2, fontSize=16, textColor=colors.HexColor('#0f172a')))
        ],
        [
            Paragraph("120 Auto Drive, Houston, TX<br/>Phone: (555) 123-AUTO<br/>support@automotivecare.com", meta_style),
            Paragraph("<b>Invoice No:</b> AC-2026-88741<br/><b>Date:</b> July 1, 2026<br/><b>Status:</b> Pending Approval", header_right)
        ]
    ]
    
    header_table = Table(header_data, colWidths=[270, 260])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    # Customer Info
    story.append(Paragraph("<b>BILL TO:</b>", ParagraphStyle('BillToHeader', parent=meta_style, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#0f172a'))))
    story.append(Paragraph("Simulated Sandbox Client<br/>Phone: +1234567<br/>Account Code: SANDBOX-99", meta_style))
    story.append(Spacer(1, 15))

    # Invoice Items Table
    body_style = ParagraphStyle(
        'InvoiceBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    
    body_right = ParagraphStyle(
        'InvoiceBodyRight',
        parent=body_style,
        alignment=2
    )

    invoice_data = [
        [
            Paragraph("<b>Service / Item Description</b>", body_style),
            Paragraph("<b>Quantity / Hours</b>", body_style),
            Paragraph("<b>Rate / Price</b>", body_style),
            Paragraph("<b>Line Total</b>", body_right)
        ],
        [
            Paragraph("<b>Full Engine Diagnostic Scan</b><br/>OBD-II scanner diagnostics and fault code analysis.", body_style),
            Paragraph("1.0", body_style),
            Paragraph("$89.00", body_style),
            Paragraph("$89.00", body_right)
        ],
        [
            Paragraph("<b>Premium Exterior & Interior Detailing</b><br/>Clay bar polish, leather conditioning, and wax protectant.", body_style),
            Paragraph("1.0", body_style),
            Paragraph("$150.00", body_style),
            Paragraph("$150.00", body_right)
        ],
        [
            Paragraph("<b>Cylinder Spark Plug Replacement</b><br/>Replaced full set of spark plugs to resolve cylinder misfires.", body_style),
            Paragraph("1.0", body_style),
            Paragraph("$120.00", body_style),
            Paragraph("$120.00", body_right)
        ],
        [
            Paragraph("<b>ASE Certified Mechanic Labor</b><br/>Diagnostics, spark plug install, and standard vehicle checkup.", body_style),
            Paragraph("3.0 hours", body_style),
            Paragraph("$110.00", body_style),
            Paragraph("$330.00", body_right)
        ],
        # Totals Section
        [
            Paragraph("", body_style),
            Paragraph("", body_style),
            Paragraph("<b>Subtotal</b>", body_style),
            Paragraph("$689.00", body_right)
        ],
        [
            Paragraph("", body_style),
            Paragraph("", body_style),
            Paragraph("<b>Sales Tax (8.25%)</b>", body_style),
            Paragraph("$56.84", body_right)
        ],
        [
            Paragraph("", body_style),
            Paragraph("", body_style),
            Paragraph("<b>TOTAL DUE</b>", ParagraphStyle('TotB', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#1d4ed8'))),
            Paragraph("<b>$745.84</b>", ParagraphStyle('TotR', parent=body_right, fontName='Helvetica-Bold', textColor=colors.HexColor('#1d4ed8')))
        ]
    ]

    t = Table(invoice_data, colWidths=[290, 80, 80, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#eff6ff')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#1e40af')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('LINEBELOW', (0,0), (-1,4), 0.5, colors.HexColor('#e2e8f0')),
        ('LINEABOVE', (2,5), (-1,5), 1, colors.HexColor('#94a3b8')),
        ('LINEBELOW', (2,-1), (-1,-1), 1.5, colors.HexColor('#1d4ed8')),
    ]))
    
    story.append(t)
    story.append(Spacer(1, 25))
    
    # Terms
    story.append(Paragraph("<b>Terms & Conditions:</b>", ParagraphStyle('TermsH', parent=meta_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#0f172a'))))
    story.append(Paragraph("Payment is due within 14 days of invoice. Standard shop warranty covers all labor and parts for 12 months or 12,000 miles. Thank you for choosing Automotive Care!", ParagraphStyle('TermsB', parent=meta_style, fontSize=8, leading=11)))
    
    doc.build(story)
    print("Invoice PDF generated successfully!")

if __name__ == "__main__":
    copy_images()
    build_furniture_catalog()
    build_invoice_pdf()
