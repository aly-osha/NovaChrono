import io
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm


def generate_invoice_pdf(invoice):
    """
    Generates a professional, print-ready A4 PDF invoice using ReportLab.
    Returns bytes in a BytesIO buffer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"NovaChrono_Invoice_{invoice.invoice_number}"
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_title = ParagraphStyle(
        'BrandTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#111111'),
    )

    brand_sub = ParagraphStyle(
        'BrandSub',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#6342FF'),
    )

    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#111111'),
    )

    meta_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#777777'),
    )

    meta_value = ParagraphStyle(
        'MetaValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#111111'),
    )

    body_cell = ParagraphStyle(
        'BodyCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#222222'),
    )

    body_cell_bold = ParagraphStyle(
        'BodyCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#111111'),
    )

    right_cell = ParagraphStyle(
        'RightCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=colors.HexColor('#222222'),
    )

    right_cell_bold = ParagraphStyle(
        'RightCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        alignment=2,
        textColor=colors.HexColor('#111111'),
    )

    footer_text = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        alignment=1,
        textColor=colors.HexColor('#666666'),
    )

    story = []

    # 1. Header Section: Brand on Left, Invoice Details on Right
    store = invoice.order.store_name if hasattr(invoice.order, 'store_name') else invoice.store_name
    header_left = [
        Paragraph("NOVACHRONO", brand_title),
        Paragraph("Collect. Discover. Trade. — Authentic Collectibles Store", brand_sub),
        Spacer(1, 4 * mm),
        Paragraph(f"<b>Store:</b> {invoice.store_name}", meta_value),
        Paragraph(f"{invoice.store_address.replace(chr(10), ', ')}", meta_value),
        Paragraph(f"Email: {invoice.store_email} | Tel: {invoice.store_phone}", meta_value),
        Paragraph(f"Tax / GSTIN ID: {invoice.store_tax_id}", meta_value),
    ]

    header_right = [
        Paragraph("OFFICIAL INVOICE", h2_style),
        Spacer(1, 2 * mm),
        Paragraph(f"<b>Invoice Number:</b> {invoice.invoice_number}", meta_value),
        Paragraph(f"<b>Order Number:</b> {invoice.order.order_number}", meta_value),
        Paragraph(f"<b>Issue Date:</b> {invoice.issue_date.strftime('%B %d, %Y')}", meta_value),
        Paragraph(f"<b>Payment Status:</b> {invoice.order.payment.get_status_display() if hasattr(invoice.order, 'payment') else 'PAID'}", meta_value),
        Paragraph(f"<b>Order Status:</b> {invoice.order.get_status_display()}", meta_value),
    ]

    header_table = Table([[header_left, header_right]], colWidths=[105 * mm, 75 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6 * mm))

    # Decorative brand colored divider line
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#6342FF'), spaceAfter=5 * mm))

    # 2. Billing & Shipping Blocks
    cust_left = [
        Paragraph("BILLED TO", meta_label),
        Spacer(1, 1 * mm),
        Paragraph(f"<b>{invoice.customer_name}</b>", meta_value),
        Paragraph(f"Email: {invoice.customer_email}", meta_value),
        Paragraph(f"Phone: {invoice.customer_phone}", meta_value),
        Paragraph(invoice.billing_address.replace('\n', '<br/>') if invoice.billing_address else invoice.shipping_address.replace('\n', '<br/>'), meta_value),
    ]

    cust_right = [
        Paragraph("SHIPPED TO", meta_label),
        Spacer(1, 1 * mm),
        Paragraph(f"<b>{invoice.order.shipping_name}</b>", meta_value),
        Paragraph(invoice.shipping_address.replace('\n', '<br/>'), meta_value),
        Paragraph(f"Carrier: {invoice.order.carrier}", meta_value),
        Paragraph(f"Tracking: {invoice.order.tracking_number if invoice.order.tracking_number else 'Assigned upon dispatch'}", meta_value),
    ]

    address_table = Table([[cust_left, cust_right]], colWidths=[90 * mm, 90 * mm])
    address_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#F8F7F4')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8F7F4')),
        ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor('#E5E2DC')),
        ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor('#E5E2DC')),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(address_table)
    story.append(Spacer(1, 6 * mm))

    # 3. Itemized Products Table
    table_data = [
        [
            Paragraph("<b>#</b>", body_cell_bold),
            Paragraph("<b>ITEM DESCRIPTION</b>", body_cell_bold),
            Paragraph("<b>TCG / SKU</b>", body_cell_bold),
            Paragraph("<b>QTY</b>", right_cell_bold),
            Paragraph("<b>UNIT PRICE</b>", right_cell_bold),
            Paragraph("<b>SUBTOTAL</b>", right_cell_bold),
        ]
    ]

    idx = 1
    for item in invoice.items.all():
        table_data.append([
            Paragraph(str(idx), body_cell),
            Paragraph(item.product_name, body_cell_bold),
            Paragraph(f"{item.tcg} <br/><font color='#777777'>{item.sku}</font>", body_cell),
            Paragraph(str(item.quantity), right_cell),
            Paragraph(f"${item.unit_price:.2f}", right_cell),
            Paragraph(f"${item.subtotal:.2f}", right_cell_bold),
        ])
        idx += 1

    items_table = Table(
        table_data,
        colWidths=[8 * mm, 72 * mm, 40 * mm, 16 * mm, 22 * mm, 22 * mm]
    )

    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#111111')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#EAE7E0')),
    ]
    # Header cells text color white
    for c in range(6):
        t_style.append(('TEXTCOLOR', (c, 0), (c, 0), colors.white))

    items_table.setStyle(TableStyle(t_style))
    story.append(items_table)
    story.append(Spacer(1, 5 * mm))

    # 4. Totals Summary Box
    summary_data = [
        [Paragraph("Items Subtotal:", meta_label), Paragraph(f"${invoice.subtotal:.2f}", right_cell)],
        [Paragraph("Estimated Tax (GST/VAT):", meta_label), Paragraph(f"${invoice.tax_amount:.2f}", right_cell)],
        [Paragraph("Shipping & Handling:", meta_label), Paragraph(f"${invoice.shipping_amount:.2f}" if invoice.shipping_amount > 0 else "FREE", right_cell)],
    ]
    if invoice.discount_amount > 0:
        summary_data.append([
            Paragraph("Promotional Discount:", meta_label),
            Paragraph(f"-${invoice.discount_amount:.2f}", right_cell)
        ])
    summary_data.append([
        Paragraph("<b>GRAND TOTAL (USD):</b>", ParagraphStyle('GrandTotalL', parent=h2_style, fontSize=11, textColor=colors.HexColor('#6342FF'))),
        Paragraph(f"<b>${invoice.grand_total:.2f}</b>", ParagraphStyle('GrandTotalR', parent=h2_style, fontSize=12, alignment=2, textColor=colors.HexColor('#6342FF')))
    ])

    summary_table = Table(summary_data, colWidths=[45 * mm, 35 * mm])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#6342FF')),
    ]))

    # Payment Badge info on left, Totals on right
    payment_info = [
        Paragraph("PAYMENT INFORMATION", meta_label),
        Spacer(1, 1 * mm),
        Paragraph(f"<b>Method:</b> {invoice.order.payment.get_payment_method_display() if hasattr(invoice.order, 'payment') else 'Vault Card'}", meta_value),
        Paragraph(f"<b>Card:</b> {invoice.order.payment.card_brand if hasattr(invoice.order, 'payment') else 'Visa'} ending in **** {invoice.order.payment.card_last4 if hasattr(invoice.order, 'payment') else '4242'}", meta_value),
        Paragraph(f"<b>Transaction Ref:</b> {invoice.order.payment.transaction_reference if hasattr(invoice.order, 'payment') else invoice.invoice_number}", meta_value),
        Spacer(1, 2 * mm),
        Paragraph("<font color='#00875A'><b>✓ PAYMENT AUTHORIZED &amp; VERIFIED</b></font>", meta_value),
    ]

    totals_row = Table([[payment_info, summary_table]], colWidths=[100 * mm, 80 * mm])
    totals_row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(totals_row)
    story.append(Spacer(1, 10 * mm))

    # 5. Terms & Guarantee Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CCCCCC'), spaceAfter=4 * mm))
    story.append(Paragraph(
        "<b>100% Authenticity Guarantee:</b> Every trading card, sealed booster box, and single card from NovaChrono is verified by certified store specialists prior to dispatch.<br/>"
        "Return requests must be initiated within 7 days of delivery for sealed goods. For support, please contact support@novachrono.com with your invoice number.",
        footer_text
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
