"""
orders/pdf.py — Official Invoice PDF generator for NovaChrono orders.
Uses ReportLab to build high-fidelity, printable, professional invoices.
"""
import io
import os
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_invoice_pdf(order):
    """
    Generates a professional PDF invoice for the given Order instance.
    Returns bytes of the PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )

    styles = getSampleStyleSheet()

    # Brand Colors
    c_primary = colors.HexColor("#0F172A")    # Deep Slate
    c_accent = colors.HexColor("#6342FF")     # Nova Royal Purple
    c_text = colors.HexColor("#1E293B")       # Dark Charcoal text
    c_muted = colors.HexColor("#64748B")      # Slate Muted text
    c_bg_light = colors.HexColor("#F8FAFC")   # Light Slate Box
    c_border = colors.HexColor("#E2E8F0")     # Light Border
    c_green = colors.HexColor("#10B981")      # Emerald Success

    # Typography styles
    brand_title = ParagraphStyle(
        "BrandTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=c_primary,
    )
    brand_sub = ParagraphStyle(
        "BrandSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=c_muted,
    )
    invoice_title = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=2,  # Right aligned
        textColor=c_accent,
    )
    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=c_muted,
    )
    meta_val = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=c_text,
    )
    meta_val_right = ParagraphStyle(
        "MetaValRight",
        parent=meta_val,
        alignment=2,
    )
    cell_text = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=c_text,
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=c_text,
    )
    cell_right = ParagraphStyle(
        "CellRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=c_text,
    )
    cell_right_bold = ParagraphStyle(
        "CellRightBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=c_text,
    )
    th_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )
    th_style_right = ParagraphStyle(
        "TableHeaderRight",
        parent=th_style,
        alignment=2,
    )
    footer_text = ParagraphStyle(
        "FooterText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        alignment=1,  # Centered
        textColor=c_muted,
    )

    story = []

    # 1. Header: Store info with Logo (left) & Invoice info (right)
    logo_path = os.path.join(settings.BASE_DIR, "static", "img", "novachrono-logo.png")
    logo_flowable = None
    if os.path.exists(logo_path):
        try:
            logo_flowable = RLImage(logo_path, width=22 * mm, height=22 * mm)
        except Exception:
            logo_flowable = None

    if logo_flowable:
        brand_top_table = Table(
            [[logo_flowable, [
                Paragraph("NOVACHRONO", brand_title),
                Paragraph("Curated Trading Card Games & Verified Collectibles", brand_sub),
            ]]],
            colWidths=[25 * mm, 80 * mm],
        )
        brand_top_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        header_left = [
            brand_top_table,
            Spacer(1, 2.5 * mm),
            Paragraph("<b>Store:</b> NovaChrono Authentics", meta_val),
            Paragraph("1501 Collector's Way, Vault District, Mumbai, MH 400001, India", meta_val),
            Paragraph("Email: support@novachrono.com | Web: www.novachrono.com", meta_val),
            Paragraph("GSTIN / Tax ID: 27AABCN1234F1Z8", meta_val),
        ]
    else:
        header_left = [
            Paragraph("NOVACHRONO", brand_title),
            Paragraph("Curated Trading Card Games & Verified Collectibles", brand_sub),
            Spacer(1, 2 * mm),
            Paragraph("<b>Store:</b> NovaChrono Authentics", meta_val),
            Paragraph("1501 Collector's Way, Vault District, Mumbai, MH 400001, India", meta_val),
            Paragraph("Email: support@novachrono.com | Web: www.novachrono.com", meta_val),
            Paragraph("GSTIN / Tax ID: 27AABCN1234F1Z8", meta_val),
        ]

    payment = getattr(order, "payment", None)
    payment_method_str = payment.get_method_display() if payment else "N/A"
    payment_status_str = payment.get_status_display() if payment else "Pending"
    invoice_no = f"NC-INV-{order.pk:05d}"
    order_date_str = order.created_at.strftime("%B %d, %Y")

    header_right = [
        Paragraph("TAX INVOICE", invoice_title),
        Spacer(1, 2 * mm),
        Paragraph(f"<b>Invoice No:</b> {invoice_no}", meta_val_right),
        Paragraph(f"<b>Order ID:</b> #{order.pk}", meta_val_right),
        Paragraph(f"<b>Date:</b> {order_date_str}", meta_val_right),
        Paragraph(f"<b>Order Status:</b> {order.get_status_display()}", meta_val_right),
        Paragraph(f"<b>Payment Status:</b> {payment_status_str}", meta_val_right),
    ]

    header_table = Table([[header_left, header_right]], colWidths=[105 * mm, 77 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # Decorative Rule
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceAfter=4 * mm))

    # 2. Billed To & Shipped To Blocks
    buyer = order.buyer
    billed_name = buyer.get_full_name() or buyer.email
    shipped_name = order.shipping_name or billed_name
    shipped_line1 = order.shipping_address_line1 or (order.shipping_address.line1 if order.shipping_address else "")
    shipped_line2 = order.shipping_address_line2 or (order.shipping_address.line2 if order.shipping_address else "")
    shipped_city = order.shipping_city or (order.shipping_address.city if order.shipping_address else "")
    shipped_state = order.shipping_state or (order.shipping_address.state if order.shipping_address else "")
    shipped_postal = order.shipping_postal_code or (order.shipping_address.postal_code if order.shipping_address else "")
    shipped_country = order.shipping_country or (order.shipping_address.country if order.shipping_address else "India")

    cust_left = [
        Paragraph("BILLED TO", meta_label),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>{billed_name}</b>", meta_val),
        Paragraph(f"Email: {buyer.email}", meta_val),
        Paragraph(f"Phone: {buyer.phone or 'Not provided'}", meta_val),
    ]

    shipped_address_parts = [shipped_line1]
    if shipped_line2:
        shipped_address_parts.append(shipped_line2)
    shipped_address_parts.append(f"{shipped_city}, {shipped_state} — {shipped_postal}")
    shipped_address_parts.append(shipped_country)

    cust_right = [
        Paragraph("SHIPPED TO", meta_label),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>{shipped_name}</b>", meta_val),
        Paragraph("<br/>".join(shipped_address_parts), meta_val),
    ]

    address_table = Table([[cust_left, cust_right]], colWidths=[91 * mm, 91 * mm])
    address_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, 0), c_bg_light),
        ("BACKGROUND", (1, 0), (1, 0), c_bg_light),
        ("BOX", (0, 0), (0, 0), 0.5, c_border),
        ("BOX", (1, 0), (1, 0), 0.5, c_border),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(address_table)
    story.append(Spacer(1, 5 * mm))

    # 3. Itemized Products Table
    table_data = [
        [
            Paragraph("<b>#</b>", th_style),
            Paragraph("<b>ITEM / DESCRIPTION</b>", th_style),
            Paragraph("<b>TCG / DETAILS</b>", th_style),
            Paragraph("<b>PRICE</b>", th_style_right),
            Paragraph("<b>QTY</b>", th_style_right),
            Paragraph("<b>AMOUNT</b>", th_style_right),
        ]
    ]

    idx = 1
    items = order.items.select_related("product", "product__set", "product__game", "product__single_card").all()
    for item in items:
        p = item.product
        details = []
        if p.game:
            details.append(p.game.name)
        if p.set:
            details.append(p.set.name)
        if hasattr(p, "single_card"):
            sc = p.single_card
            details.append(f"{sc.get_condition_display()} · {sc.rarity}")
        details.append("HSN: 9504 40 00")
        details_str = " · ".join(details) if details else "Collector Product · HSN: 9504 40 00"

        table_data.append([
            Paragraph(str(idx), cell_text),
            Paragraph(f"<b>{p.name}</b>", cell_bold),
            Paragraph(f"<font color='#64748B'>{details_str}</font>", cell_text),
            Paragraph(f"₹{item.unit_price:,.2f}", cell_right),
            Paragraph(str(item.quantity), cell_right),
            Paragraph(f"₹{item.line_total:,.2f}", cell_right_bold),
        ])
        idx += 1

    items_table = Table(
        table_data,
        colWidths=[10 * mm, 64 * mm, 46 * mm, 24 * mm, 14 * mm, 24 * mm],
    )
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), c_primary),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, c_border),
    ]
    # Alternating row background
    for r in range(1, len(table_data)):
        if r % 2 == 0:
            t_style.append(("BACKGROUND", (0, r), (-1, r), c_bg_light))

    items_table.setStyle(TableStyle(t_style))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    # 4. Summary & Payment Information (GST 12% under HSN 9504 40 00)
    gst_rate = Decimal("0.12")
    # Base taxable value derived from total amount (retail prices are GST-inclusive)
    taxable_val = (order.total_amount / (Decimal("1") + gst_rate)).quantize(Decimal("0.01"))
    total_tax = (order.total_amount - taxable_val).quantize(Decimal("0.01"))

    # Intra-state vs Inter-state determination (Seller registered in Maharashtra, Code 27)
    buyer_state = (shipped_state or "").strip().lower()
    is_intra_state = not buyer_state or "maharashtra" in buyer_state or buyer_state == "mh"

    summary_data = [
        [Paragraph("Taxable Value (Base):", meta_label), Paragraph(f"₹{taxable_val:,.2f}", cell_right)],
    ]
    if is_intra_state:
        cgst = (total_tax / Decimal("2")).quantize(Decimal("0.01"))
        sgst = total_tax - cgst
        summary_data.append([Paragraph("CGST (6% · HSN 9504):", meta_label), Paragraph(f"₹{cgst:,.2f}", cell_right)])
        summary_data.append([Paragraph("SGST (6% · HSN 9504):", meta_label), Paragraph(f"₹{sgst:,.2f}", cell_right)])
    else:
        igst = total_tax
        summary_data.append([Paragraph("IGST (12% · HSN 9504):", meta_label), Paragraph(f"₹{igst:,.2f}", cell_right)])

    summary_data.extend([
        [Paragraph("Total GST (12%):", meta_label), Paragraph(f"₹{total_tax:,.2f}", cell_right)],
        [Paragraph("Shipping &amp; Handling:", meta_label), Paragraph("FREE", cell_right)],
        [
            Paragraph("<b>TOTAL PAYABLE:</b>", ParagraphStyle("GTLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, textColor=c_accent)),
            Paragraph(f"<b>₹{order.total_amount:,.2f}</b>", ParagraphStyle("GTVal", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10.5, alignment=2, textColor=c_accent)),
        ],
    ])
    summary_table = Table(summary_data, colWidths=[48 * mm, 32 * mm])
    summary_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LINEABOVE", (0, -1), (-1, -1), 1, c_accent),
    ]))

    payment_info = [
        Paragraph("PAYMENT INFORMATION", meta_label),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Payment Method:</b> {payment_method_str}", meta_val),
        Paragraph(f"<b>Transaction Reference:</b> {payment.transaction_ref if payment and payment.transaction_ref else 'N/A'}", meta_val),
        Spacer(1, 1.5 * mm),
    ]
    if payment and payment.status == "success":
        payment_info.append(Paragraph("<font color='#10B981'><b>✓ PAYMENT AUTHORIZED &amp; VERIFIED</b></font>", meta_val))
    elif payment and payment.status == "pending" and payment.method == "cod":
        payment_info.append(Paragraph("<font color='#D97706'><b>PAYABLE ON DELIVERY (COD)</b></font>", meta_val))
    else:
        payment_info.append(Paragraph(f"<font color='#64748B'><b>Status: {payment_status_str}</b></font>", meta_val))

    totals_row = Table([[payment_info, summary_table]], colWidths=[102 * mm, 80 * mm])
    totals_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(totals_row)
    story.append(Spacer(1, 8 * mm))

    # 5. Guarantee & Terms Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=c_border, spaceAfter=3 * mm))
    story.append(Paragraph(
        "<b>100% Authenticity Guarantee:</b> Every single card, booster pack, and sealed box sold by NovaChrono "
        "undergoes multi-point specialist verification prior to shipment.<br/>"
        "This is an electronically generated tax invoice. For returns or support, please reach out to support@novachrono.com with your invoice number.",
        footer_text,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
