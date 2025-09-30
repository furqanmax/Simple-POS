"""
Enhanced Invoice Generator with Multi-Format Support
Supports all paper and thermal formats with automatic layout adaptation
"""
import json
import logging
import os
import io
import tempfile
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, A4, A5, letter, legal
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    Image, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas
import qrcode
from PIL import Image as PILImage

from database import db
from invoice_formats import (
    BillSize, LayoutStyle, BillFormatRegistry, 
    AutoLayoutEngine, ThermalOptimizer, LayoutConfig
)

logger = logging.getLogger(__name__)


class EnhancedInvoiceGenerator:
    """Enhanced invoice generator with multi-format support"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.registry = BillFormatRegistry()
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for different formats"""
        # Standard styles
        self.styles.add(ParagraphStyle(
            name='InvoiceTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER,
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='BusinessName',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            alignment=TA_LEFT,
            spaceAfter=6
        ))
        
        # Compact styles for thermal
        self.styles.add(ParagraphStyle(
            name='ThermalTitle',
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Courier-Bold',
            alignment=TA_CENTER,
            spaceAfter=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='ThermalNormal',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Courier',
            alignment=TA_LEFT
        ))
        
        # Minimal style
        self.styles.add(ParagraphStyle(
            name='MinimalHeader',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#666666'),
            alignment=TA_LEFT,
            spaceAfter=4
        ))
    
    def generate_invoice(self, order_id: int, 
                        bill_size: BillSize = BillSize.A4,
                        layout_style: LayoutStyle = LayoutStyle.CLASSIC,
                        output_path: Optional[str] = None,
                        preview_only: bool = False,
                        printer_name: Optional[str] = None) -> str:
        """
        Generate invoice with specified format and style
        
        Args:
            order_id: Order ID to generate invoice for
            bill_size: Size format for the invoice
            layout_style: Layout style to use
            output_path: Optional output path for PDF
            preview_only: If True, generates for preview only
            printer_name: Optional printer name for compatibility check
        
        Returns:
            Path to generated PDF
        """
        # Get order data
        order_data = self._fetch_order_data(order_id)
        if not order_data:
            raise ValueError(f"Order {order_id} not found")
        
        # Get layout configuration
        config = self.registry.get_default_config(bill_size, layout_style)
        
        # Check printer compatibility
        if printer_name and not preview_only:
            compatible, fallback_size = self._check_printer_compatibility(
                printer_name, bill_size
            )
            if not compatible and fallback_size:
                logger.warning(f"Printer doesn't support {bill_size.display_name}, "
                             f"using {fallback_size.display_name} instead")
                bill_size = fallback_size
                config = self.registry.get_default_config(bill_size, layout_style)
        
        # Generate output path
        if not output_path:
            output_path = self._generate_output_path(order_id, bill_size, preview_only)
        
        # Generate invoice based on format type
        if bill_size.is_thermal:
            return self._generate_thermal_invoice(order_data, config, output_path)
        else:
            return self._generate_paper_invoice(order_data, config, output_path)
    
    def _fetch_order_data(self, order_id: int) -> Optional[Dict]:
        """Fetch complete order data from database"""
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get order details
        cursor.execute("""
            SELECT o.*, u.username, t.name as template_name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            LEFT JOIN invoice_templates t ON o.invoice_template_id = t.id
            WHERE o.id = ?
        """, (order_id,))
        
        order = cursor.fetchone()
        if not order:
            return None
        
        # Get order items
        cursor.execute("""
            SELECT * FROM order_items WHERE order_id = ?
        """, (order_id,))
        items = cursor.fetchall()
        
        # Get settings
        cursor.execute("SELECT * FROM settings WHERE id = 1")
        settings = cursor.fetchone() or {}
        
        # Get business info
        template_id = order['invoice_template_id'] if order and 'invoice_template_id' in order.keys() else 1
        cursor.execute("""
            SELECT business_info_json FROM invoice_templates 
            WHERE id = ? LIMIT 1
        """, (template_id,))
        
        template = cursor.fetchone()
        business_info = {}
        if template and template['business_info_json']:
            business_info = json.loads(template['business_info_json'])
        
        return {
            'order': dict(order) if order else {},
            'items': [dict(item) for item in items] if items else [],
            'settings': dict(settings) if settings else {},
            'business_info': business_info
        }
    
    def _generate_paper_invoice(self, order_data: Dict, 
                               config: LayoutConfig, 
                               output_path: str) -> str:
        """Generate invoice for paper formats"""
        # Determine page size
        page_size_map = {
            BillSize.A3: A3,
            BillSize.A4: A4,
            BillSize.A5: A5,
            BillSize.LETTER: letter,
            BillSize.LEGAL: legal,
            BillSize.HALF_LETTER: (5.5*inch, 8.5*inch),
            BillSize.QUARTER_LETTER: (4.25*inch, 8.5*inch),
            BillSize.LONG_STRIP: (2.75*inch, 7.625*inch),
            BillSize.CASH_RECEIPT: (109*mm, 189*mm)
        }
        
        page_size = page_size_map.get(config.size, A4)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=config.margins.right * mm,
            leftMargin=config.margins.left * mm,
            topMargin=config.margins.top * mm,
            bottomMargin=config.margins.bottom * mm
        )
        
        # Build content
        story = []
        
        # Add header
        story.extend(self._build_header(order_data, config))
        
        # Add invoice info
        story.append(Spacer(1, 0.2*inch))
        story.extend(self._build_invoice_info(order_data['order'], config))
        
        # Add items table
        story.append(Spacer(1, 0.2*inch))
        story.append(self._build_items_table(order_data, config))
        
        # Add totals
        story.append(Spacer(1, 0.2*inch))
        story.append(self._build_totals(order_data, config))
        
        # Add footer with branding
        story.append(Spacer(1, 0.3*inch))
        story.extend(self._build_footer(config))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"Invoice generated: {output_path}")
        return output_path
    
    def _generate_thermal_invoice(self, order_data: Dict,
                                 config: LayoutConfig,
                                 output_path: str) -> str:
        """Generate invoice for thermal printers"""
        # Use custom canvas for thermal
        width_points = config.size.width_mm * mm
        height_points = 1000 * mm  # Start with large height
        
        c = canvas.Canvas(output_path, pagesize=(width_points, height_points))
        
        # Starting position
        y_pos = height_points - config.margins.top * mm
        x_center = width_points / 2
        x_left = config.margins.left * mm
        x_right = width_points - config.margins.right * mm
        
        # Font settings
        c.setFont("Courier-Bold", 12)
        
        # Header
        business_name = order_data['business_info'].get('name', 'Business Name')
        c.drawCentredString(x_center, y_pos, business_name)
        y_pos -= 15
        
        c.setFont("Courier", 8)
        if order_data['business_info'].get('address'):
            c.drawCentredString(x_center, y_pos, order_data['business_info']['address'])
            y_pos -= 10
        
        if order_data['business_info'].get('phone'):
            c.drawCentredString(x_center, y_pos, f"Tel: {order_data['business_info']['phone']}")
            y_pos -= 10
        
        # Separator
        y_pos -= 5
        c.line(x_left, y_pos, x_right, y_pos)
        y_pos -= 10
        
        # Invoice info
        order = order_data['order']
        c.setFont("Courier", 10)
        c.drawString(x_left, y_pos, f"Invoice: INV-{order['id']:06d}")
        y_pos -= 12
        
        c.setFont("Courier", 8)
        c.drawString(x_left, y_pos, f"Date: {datetime.fromisoformat(order['created_at']).strftime('%Y-%m-%d %H:%M')}")
        y_pos -= 10
        c.drawString(x_left, y_pos, f"Cashier: {order['username']}")
        y_pos -= 10
        
        # Separator
        y_pos -= 5
        c.line(x_left, y_pos, x_right, y_pos)
        y_pos -= 10
        
        # Items
        settings = order_data['settings']
        currency = settings.get('currency_symbol', '₹')
        
        c.setFont("Courier-Bold", 9)
        c.drawString(x_left, y_pos, "ITEM")
        c.drawRightString(x_right, y_pos, "AMOUNT")
        y_pos -= 10
        
        c.setFont("Courier", 8)
        for item in order_data['items']:
            # Item name
            item_text = f"{item['name'][:20]} x{item['quantity']:.0f}"
            amount_text = f"{currency}{item['line_total']:.2f}"
            
            c.drawString(x_left, y_pos, item_text)
            c.drawRightString(x_right, y_pos, amount_text)
            y_pos -= 10
        
        # Separator
        y_pos -= 5
        c.line(x_left, y_pos, x_right, y_pos)
        y_pos -= 10
        
        # Totals
        c.setFont("Courier", 9)
        c.drawString(x_left, y_pos, "Subtotal:")
        c.drawRightString(x_right, y_pos, f"{currency}{order['subtotal']:.2f}")
        y_pos -= 10
        
        c.drawString(x_left, y_pos, f"Tax ({order['tax_rate']:.1f}%):")
        c.drawRightString(x_right, y_pos, f"{currency}{order['tax_total']:.2f}")
        y_pos -= 10
        
        # Double line for total
        y_pos -= 3
        c.line(x_left, y_pos, x_right, y_pos)
        y_pos -= 2
        c.line(x_left, y_pos, x_right, y_pos)
        y_pos -= 10
        
        c.setFont("Courier-Bold", 11)
        c.drawString(x_left, y_pos, "TOTAL:")
        c.drawRightString(x_right, y_pos, f"{currency}{order['grand_total']:.2f}")
        y_pos -= 15
        
        # Footer
        c.setFont("Courier", 9)
        c.drawCentredString(x_center, y_pos, "Thank you for your business!")
        y_pos -= 10
        
        c.setFont("Courier", 8)
        c.drawCentredString(x_center, y_pos, "Powered by POS System")
        y_pos -= 10
        c.drawCentredString(x_center, y_pos, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Calculate actual height used and set page size
        content_height = height_points - y_pos + config.margins.bottom * mm
        c._pagesize = (width_points, content_height)
        
        c.save()
        
        logger.info(f"Thermal invoice generated: {output_path}")
        return output_path
    
    def _build_header(self, order_data: Dict, config: LayoutConfig) -> List:
        """Build invoice header"""
        story = []
        business_info = order_data['business_info']
        
        if business_info.get('name'):
            story.append(Paragraph(business_info['name'], self.styles['BusinessName']))
        
        info_lines = []
        if business_info.get('address'):
            info_lines.append(business_info['address'])
        if business_info.get('phone'):
            info_lines.append(f"Phone: {business_info['phone']}")
        if business_info.get('email'):
            info_lines.append(f"Email: {business_info['email']}")
        if business_info.get('tax_id'):
            info_lines.append(f"Tax ID: {business_info['tax_id']}")
        
        if info_lines:
            info_text = '<br/>'.join(info_lines)
            story.append(Paragraph(info_text, self.styles['Normal']))
        
        return story
    
    def _build_invoice_info(self, order: Dict, config: LayoutConfig) -> List:
        """Build invoice information section"""
        story = []
        
        invoice_data = [
            ['Invoice #:', f"INV-{order['id']:06d}"],
            ['Date:', datetime.fromisoformat(order['created_at']).strftime('%Y-%m-%d %H:%M')],
            ['Operator:', order['username']],
            ['Status:', order['status'].upper()]
        ]
        
        invoice_table = Table(invoice_data, colWidths=[1.5*inch, 2*inch])
        invoice_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(invoice_table)
        return story
    
    def _build_items_table(self, order_data: Dict, config: LayoutConfig) -> Table:
        """Build items table"""
        items = order_data['items']
        settings = order_data['settings']
        currency = settings.get('currency_symbol', '₹')
        
        # Table data
        data = [['Item', 'Qty', 'Unit Price', 'Total']]
        
        for item in items:
            data.append([
                item['name'],
                f"{item['quantity']:.2f}",
                f"{currency}{item['unit_price']:.2f}",
                f"{currency}{item['line_total']:.2f}"
            ])
        
        # Calculate column widths
        total_width = config.printable_width_mm * mm
        col_widths = [
            total_width * 0.4,
            total_width * 0.15,
            total_width * 0.2,
            total_width * 0.25
        ]
        
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]))
        
        return table
    
    def _build_totals(self, order_data: Dict, config: LayoutConfig) -> Table:
        """Build totals section"""
        order = order_data['order']
        settings = order_data['settings']
        currency = settings.get('currency_symbol', '₹')
        
        data = [
            ['Subtotal:', f"{currency}{order['subtotal']:.2f}"],
            [f"Tax ({order['tax_rate']:.1f}%):", f"{currency}{order['tax_total']:.2f}"],
            ['Grand Total:', f"{currency}{order['grand_total']:.2f}"]
        ]
        
        table = Table(data, colWidths=[1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ]))
        
        # Right align the totals table
        wrapper_data = [['', table]]
        wrapper_table = Table(wrapper_data, colWidths=[4*inch, 3*inch])
        
        return wrapper_table
    
    def _build_footer(self, config: LayoutConfig) -> List:
        """Build footer with branding"""
        story = []
        
        footer_style = ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER
        )
        
        story.append(Paragraph("<b>Powered by POS System</b>", footer_style))
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            footer_style
        ))
        
        return story
    
    def _check_printer_compatibility(self, printer_name: str, 
                                    bill_size: BillSize) -> Tuple[bool, Optional[BillSize]]:
        """Check if printer supports the selected size"""
        # Mock implementation - would integrate with actual printer API
        return True, None
    
    def _generate_output_path(self, order_id: int, 
                             bill_size: BillSize,
                             preview: bool) -> str:
        """Generate output path for invoice PDF"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        size_suffix = bill_size.name.lower()
        preview_suffix = "_preview" if preview else ""
        
        filename = f"invoice_{order_id}_{size_suffix}{preview_suffix}_{timestamp}.pdf"
        
        # Get invoice folder
        invoice_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            'invoices'
        )
        os.makedirs(invoice_folder, exist_ok=True)
        
        return os.path.join(invoice_folder, filename)
