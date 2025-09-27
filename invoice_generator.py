"""
Invoice PDF generation with templates, logos, and QR codes
"""
import json
import logging
import os
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus.flowables import KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import qrcode
from PIL import Image as PILImage
from database import db

logger = logging.getLogger(__name__)

class InvoiceGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
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
        
        self.styles.add(ParagraphStyle(
            name='BusinessInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_LEFT,
            leading=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='InvoiceDetails',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            alignment=TA_RIGHT
        ))
    
    def generate_invoice(self, order_id, output_path=None, use_snapshot=False):
        """Generate invoice PDF for an order"""
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
            raise ValueError(f"Order {order_id} not found")
        
        # Get order items
        cursor.execute("""
            SELECT * FROM order_items WHERE order_id = ?
        """, (order_id,))
        items = cursor.fetchall()
        
        # Use snapshot if requested and available
        if use_snapshot and order['invoice_snapshot_json']:
            snapshot = json.loads(order['invoice_snapshot_json'])
            template_data = snapshot.get('template', {})
            settings = snapshot.get('settings', {})
        else:
            # Get current template data
            template_data = self._get_template_data(order['invoice_template_id'])
            # Get current settings
            cursor.execute("SELECT * FROM settings WHERE id = 1")
            settings_row = cursor.fetchone()
            settings = dict(settings_row) if settings_row else {}
            
            # Get user preferences to override currency if set
            cursor.execute("""
                SELECT currency_symbol FROM user_preferences 
                WHERE user_id = ?
            """, (order['user_id'],))
            user_prefs = cursor.fetchone()
            
            if user_prefs and user_prefs['currency_symbol']:
                settings['currency_symbol'] = user_prefs['currency_symbol']
        
        # Generate filename if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"invoice_{order_id}_{timestamp}.pdf"
            
            # Get invoice folder from settings
            invoice_folder = settings.get('invoice_folder', 'invoices')
            if not os.path.isabs(invoice_folder):
                # If relative path, make it relative to the app directory
                invoice_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), invoice_folder)
            
            # Create folder if it doesn't exist
            os.makedirs(invoice_folder, exist_ok=True)
            
            # Full path to the invoice
            output_path = os.path.join(invoice_folder, filename)
        
        # Determine page size
        page_size = A4 if settings.get('page_size', 'A4') == 'A4' else letter
        
        # Create PDF
        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            rightMargin=20,
            leftMargin=20,
            topMargin=30,
            bottomMargin=30
        )
        
        # Build invoice content
        story = []
        
        # Add header with logo and business info
        story.extend(self._build_header(template_data, order_id))
        
        # Add invoice details
        story.append(Spacer(1, 0.3*inch))
        story.extend(self._build_invoice_info(order, settings))
        
        # Add items table
        story.append(Spacer(1, 0.3*inch))
        story.append(self._build_items_table(items, settings))
        
        # Add totals
        story.append(Spacer(1, 0.2*inch))
        story.append(self._build_totals_table(order, settings))
        
        # Add QR codes if configured
        qr_codes = self._get_qr_codes(order['invoice_template_id'])
        if qr_codes:
            story.append(Spacer(1, 0.3*inch))
            story.extend(self._build_qr_codes(qr_codes))
        
        # Add footer
        story.append(Spacer(1, 0.5*inch))
        story.extend(self._build_footer(template_data))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"Invoice generated for order {order_id}: {output_path}")
        return output_path
    
    def _get_template_data(self, template_id):
        """Get template data from database"""
        if not template_id:
            return {}
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM invoice_templates WHERE id = ?
        """, (template_id,))
        
        template = cursor.fetchone()
        if not template:
            return {}
        
        return {
            'template_id': template_id,  # Include template_id for logo retrieval
            'name': template['name'],
            'header': json.loads(template['header_json'] or '{}'),
            'footer': json.loads(template['footer_json'] or '{}'),
            'styles': json.loads(template['styles_json'] or '{}'),
            'business_info': json.loads(template['business_info_json'] or '{}')
        }
    
    def _get_logo_image(self, template_id):
        """Get logo image from database and convert to ReportLab Image"""
        if not template_id:
            return None
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT blob, meta_json FROM invoice_assets
            WHERE template_id = ? AND type = 'logo' AND storage_kind = 'blob'
            ORDER BY created_at DESC LIMIT 1
        """, (template_id,))
        
        logo_asset = cursor.fetchone()
        if not logo_asset or not logo_asset['blob']:
            return None
        
        try:
            # Convert blob to Image
            logo_bytes = io.BytesIO(logo_asset['blob'])
            
            # Open with PIL first to resize if needed
            pil_image = PILImage.open(logo_bytes)
            
            # Resize if too large (max width 150 pixels)
            max_width = 150
            if pil_image.width > max_width:
                ratio = max_width / pil_image.width
                new_height = int(pil_image.height * ratio)
                pil_image = pil_image.resize((max_width, new_height), PILImage.Resampling.LANCZOS)
            
            # Convert back to bytes for ReportLab
            img_buffer = io.BytesIO()
            pil_image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Create ReportLab Image
            return Image(img_buffer, width=pil_image.width, height=pil_image.height)
            
        except Exception as e:
            logger.error(f"Error loading logo image: {e}")
            return None
    
    def _get_qr_codes(self, template_id):
        """Get QR codes for template"""
        if not template_id:
            return []
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM invoice_assets 
            WHERE template_id = ? AND type = 'qr'
        """, (template_id,))
        
        qr_codes = []
        for row in cursor.fetchall():
            meta = json.loads(row['meta_json'] or '{}')
            qr_codes.append({
                'payload': meta.get('payload', ''),
                'label': meta.get('label', ''),
                'size': meta.get('size', 100),
                'error_correction': meta.get('error_correction', 'M')
            })
        
        return qr_codes
    
    def _build_header(self, template_data, order_id):
        """Build invoice header with logo and business info"""
        story = []
        
        business_info = template_data.get('business_info', {})
        header = template_data.get('header', {})
        
        # Get logo if show_logo is enabled
        logo_image = None
        if header.get('show_logo', False):
            logo_image = self._get_logo_image(template_data.get('template_id'))
        
        # If we have a logo and business info, create a table layout
        if logo_image and header.get('show_business_info', True) and business_info:
            # Create a table with logo on left, business info on right
            logo_cell = []
            logo_cell.append(logo_image)
            
            info_cell = []
            if business_info.get('name'):
                info_cell.append(Paragraph(business_info['name'], self.styles['BusinessName']))
            
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
                info_cell.append(Paragraph(info_text, self.styles['BusinessInfo']))
            
            # Create table with logo and info
            header_data = [[logo_cell, info_cell]]
            header_table = Table(header_data, colWidths=[2.5*inch, 4.5*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 0.2*inch))
            
        # If no logo, display business info normally
        elif header.get('show_business_info', True) and business_info:
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
                story.append(Paragraph(info_text, self.styles['BusinessInfo']))
            story.append(Spacer(1, 0.2*inch))
        
        # Add invoice title
        if header.get('title'):
            story.append(Paragraph(header['title'], self.styles['InvoiceTitle']))
            story.append(Spacer(1, 0.2*inch))
        
        return story
    
    def _build_invoice_info(self, order, settings):
        """Build invoice information section"""
        story = []
        
        # Create invoice details table
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
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
        ]))
        
        # Position invoice info on the right
        wrapper_data = [['', invoice_table]]
        wrapper_table = Table(wrapper_data, colWidths=[3.5*inch, 3.5*inch])
        
        story.append(wrapper_table)
        
        return story
    
    def _build_items_table(self, items, settings):
        """Build items table"""
        currency = settings.get('currency_symbol', '$')
        
        # Table headers
        data = [['Item', 'Qty', 'Unit Price', 'Total']]
        
        # Add items
        for item in items:
            data.append([
                item['name'],
                f"{item['quantity']:.2f}",
                f"{currency}{item['unit_price']:.2f}",
                f"{currency}{item['line_total']:.2f}"
            ])
        
        # Create table
        table = Table(data, colWidths=[3.5*inch, 1*inch, 1.25*inch, 1.25*inch])
        
        # Apply styles
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (3, -1), 'RIGHT'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ]))
        
        return table
    
    def _build_totals_table(self, order, settings):
        """Build totals table"""
        currency = settings.get('currency_symbol', '$')
        
        data = [
            ['Subtotal:', f"{currency}{order['subtotal']:.2f}"],
            [f"Tax ({order['tax_rate']:.1f}%):", f"{currency}{order['tax_total']:.2f}"],
            ['Grand Total:', f"{currency}{order['grand_total']:.2f}"]
        ]
        
        table = Table(data, colWidths=[1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
            ('TOPPADDING', (0, -1), (-1, -1), 6),
        ]))
        
        # Position totals on the right
        wrapper_data = [['', table]]
        wrapper_table = Table(wrapper_data, colWidths=[4*inch, 3*inch])
        
        return wrapper_table
    
    def _build_qr_codes(self, qr_codes):
        """Build QR codes section"""
        story = []
        
        for qr_data in qr_codes:
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=getattr(qrcode.constants, f"ERROR_CORRECT_{qr_data['error_correction']}", qrcode.constants.ERROR_CORRECT_M),
                box_size=10,
                border=4,
            )
            
            qr.add_data(qr_data['payload'])
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to ReportLab image
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            qr_image = Image(img_buffer, width=qr_data['size'], height=qr_data['size'])
            
            # Add label if provided
            if qr_data.get('label'):
                label = Paragraph(qr_data['label'], self.styles['Normal'])
                story.append(KeepTogether([qr_image, label]))
            else:
                story.append(qr_image)
        
        return story
    
    def _build_footer(self, template_data):
        """Build invoice footer"""
        story = []
        
        footer = template_data.get('footer', {})
        
        if footer.get('text'):
            footer_style = ParagraphStyle(
                name='Footer',
                parent=self.styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#666666'),
                alignment=TA_CENTER
            )
            story.append(Paragraph(footer['text'], footer_style))
        
        if footer.get('show_date', True):
            date_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            date_style = ParagraphStyle(
                name='FooterDate',
                parent=self.styles['Normal'],
                fontSize=8,
                textColor=colors.HexColor('#999999'),
                alignment=TA_CENTER
            )
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(date_text, date_style))
        
        return story
