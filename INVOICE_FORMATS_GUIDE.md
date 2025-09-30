# 📄 Multi-Format Invoice System Documentation

## Overview
The POS System now features a comprehensive multi-format invoice generation system that supports various paper sizes and thermal printer formats with automatic layout adaptation.

## ✨ Key Features

### 🎯 Supported Formats

#### A-Series Paper Formats
- **A5**: 148 × 210 mm - Compact paper invoices
- **A4**: 210 × 297 mm - Standard business invoices
- **A3**: 297 × 420 mm - Large format detailed invoices

#### North American Formats
- **Half Letter**: 5.5 × 8.5 inches (140 × 216 mm)
- **Letter**: 8.5 × 11 inches (216 × 279 mm)
- **Legal**: 8.5 × 14 inches (216 × 356 mm)

#### Thermal Printer Formats
- **57mm Thermal**: Narrow thermal receipts
- **58mm Thermal**: Standard compact thermal
- **76mm Thermal**: Medium width thermal
- **80mm Thermal**: Standard thermal receipts

#### Special Formats
- **Quarter Letter Strip**: 4.25 × 8.5 inches
- **Long Strip**: 2.75 × 7.625 inches
- **Cash Receipt Book**: 10.9 × 18.9 cm

### 📐 Layout Styles

1. **Classic** - Traditional layout with full business details
2. **Minimal** - Clean, minimalist design without borders
3. **Compact** - Optimized for thermal printers and small formats
4. **Detailed** - Maximum information density with extended columns

## 🔧 System Architecture

### Core Components

#### 1. `invoice_formats.py`
- **BillSize Enum**: Defines all supported formats with dimensions
- **LayoutStyle Enum**: Available layout templates
- **BillFormatRegistry**: Central registry for format configurations
- **AutoLayoutEngine**: Automatic content adaptation based on format
- **ThermalOptimizer**: Special optimizations for thermal printers

#### 2. `invoice_generator_enhanced.py`
- **EnhancedInvoiceGenerator**: Main invoice generation class
- Separate rendering paths for paper and thermal formats
- Automatic format detection and adaptation
- Content pagination for large invoices

#### 3. `invoice_preview_dialog.py`
- Interactive preview dialog with format selection
- Real-time preview generation
- Format information display
- Print and save functionality

## 🎨 Automatic Layout Adaptation

### Content Fitting Rules

#### For Paper Formats
- **Item Names**: Multi-line wrapping up to 3 lines
- **Margins**: Minimum 5-10mm to prevent clipping
- **QR Codes**: Up to 3 QR codes in grid layout
- **Logo**: Scales based on format size
- **Pagination**: Automatic page breaks when content exceeds 85% of page

#### For Thermal Formats
- **Item Names**: Truncate with ellipsis to fit width
- **Margins**: Minimal 2-3mm for maximum content
- **QR Codes**: Single QR code, vertically stacked
- **Font**: Monospace for consistent alignment
- **Characters/Line**: Calculated based on paper width

### Character Per Line Budget (Thermal)
```
57mm: ~22 characters
58mm: ~23 characters  
76mm: ~30 characters
80mm: ~32 characters
```

## 📊 Format Selection Matrix

| Format | Best For | Max QR Codes | Logo Size | Pagination |
|--------|----------|--------------|-----------|------------|
| A3 | Detailed reports | 3 | 30mm | Yes |
| A4 | Standard invoices | 2 | 25mm | Yes |
| A5 | Compact invoices | 2 | 20mm | Yes |
| Letter | US standard | 2 | 25mm | Yes |
| Legal | Extended lists | 3 | 25mm | Yes |
| 80mm Thermal | POS receipts | 1 | 15mm | No |
| 58mm Thermal | Compact receipts | 1 | 12mm | No |

## 🖨️ Printer Compatibility

### Automatic Fallback System
1. System checks printer capabilities
2. If selected size unsupported, finds closest match
3. Warns user about fallback
4. Scales content appropriately

### Printer Profiles
- Store supported sizes per printer
- Custom margin capabilities
- Thermal vs paper classification
- Default printer selection

## 💾 Database Schema Updates

### Settings Table
```sql
default_bill_size TEXT DEFAULT 'A4'
default_bill_layout TEXT DEFAULT 'classic'  
thermal_density INTEGER DEFAULT 32
per_size_margins_json TEXT
font_scale_override DECIMAL(3,2)
```

### Invoice Templates Table
```sql
preferred_bill_size TEXT
preferred_layout TEXT
size_overrides_json TEXT
```

### Printer Profiles Table
```sql
CREATE TABLE printer_profiles (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    device_name TEXT,
    supported_sizes_json TEXT,
    margin_caps_json TEXT,
    is_thermal BOOLEAN,
    is_default BOOLEAN
)
```

## 🚀 Usage Guide

### Basic Invoice Generation
```python
from invoice_generator_enhanced import EnhancedInvoiceGenerator
from invoice_formats import BillSize, LayoutStyle

generator = EnhancedInvoiceGenerator()

# Generate A4 classic invoice
pdf_path = generator.generate_invoice(
    order_id=123,
    bill_size=BillSize.A4,
    layout_style=LayoutStyle.CLASSIC
)

# Generate thermal receipt
pdf_path = generator.generate_invoice(
    order_id=123,
    bill_size=BillSize.THERMAL_80,
    layout_style=LayoutStyle.COMPACT
)
```

### Using Preview Dialog
```python
from invoice_preview_dialog import show_invoice_preview

# Show interactive preview with format selection
show_invoice_preview(parent_window, order_id, auth_manager)
```

### Setting Defaults
1. Open Settings tab (Admin only)
2. Select "Invoice Formats" section
3. Choose default bill size from dropdown
4. Select default layout style
5. Click "Save Settings"

## 🧪 Validation & Edge Cases

### Handled Scenarios
✅ **Long item names**: Wrap on paper, truncate on thermal
✅ **Many line items**: Automatic pagination with "Continued..." headers
✅ **Zero margins**: Enforce minimum to prevent clipping
✅ **Unsupported printer size**: Automatic fallback to closest supported
✅ **Oversized QR/logos**: Auto-scale with minimum scannable size
✅ **Mixed character sets**: Support for INR (₹) and Indian number format
✅ **Different DPI**: DPI-agnostic PDF rendering
✅ **Continuous feed**: Dynamic height calculation for thermal

### Performance Targets
- Thermal rendering: < 300ms
- A4 rendering: < 1 second for 100 items
- Preview generation: < 500ms
- Format switching: Instant

## 🔄 Workflow

### Invoice Generation Flow
1. User finalizes order
2. Preview dialog opens with last used format
3. User can change format and see instant preview
4. User clicks Print or Save PDF
5. System validates printer compatibility
6. Falls back if needed with user confirmation
7. Generates final PDF with selected format
8. Sends to printer or saves to disk

### Template Priority
1. Template preferred size (if set)
2. User's last selection
3. System default setting
4. Fallback to A4 Classic

## 📋 Configuration Examples

### Thermal Receipt Configuration
```python
config = LayoutConfig(
    size=BillSize.THERMAL_80,
    style=LayoutStyle.COMPACT,
    margins=Margins(3, 3, 3, 3),
    fonts=FontSettings(
        base_size=9,
        mono_font="Courier"
    ),
    chars_per_line=32,
    max_qr_codes=1,
    wrap_item_names=False
)
```

### A4 Invoice Configuration
```python
config = LayoutConfig(
    size=BillSize.A4,
    style=LayoutStyle.CLASSIC,
    margins=Margins(15, 15, 15, 15),
    fonts=FontSettings(
        base_size=10,
        sans_font="Helvetica"
    ),
    max_qr_codes=2,
    wrap_item_names=True,
    max_lines_per_item=3
)
```

## 🎯 Best Practices

### For Developers
1. Always check format compatibility before printing
2. Use preview dialog for user-facing operations
3. Cache generated PDFs for quick reprints
4. Handle printer errors gracefully
5. Test with various content lengths

### For Users
1. Set appropriate defaults for your business
2. Use thermal formats for quick receipts
3. Use A4/Letter for formal invoices
4. Preview before printing expensive formats
5. Save printer profiles for quick switching

## 🐛 Troubleshooting

### Common Issues

**Issue**: Thermal receipt text cut off
- **Solution**: Reduce font size or use narrower format

**Issue**: QR code not scanning
- **Solution**: Increase QR size or reduce error correction

**Issue**: Printer rejects format
- **Solution**: Check printer profile, use fallback size

**Issue**: Slow generation for large invoices
- **Solution**: Enable pagination, reduce image quality

**Issue**: Margins too small warning
- **Solution**: Use minimum margins for format type

## 📊 Format Comparison Table

| Aspect | Paper Formats | Thermal Formats |
|--------|--------------|-----------------|
| **Layout** | Multi-column | Single column |
| **Font** | Proportional | Monospace |
| **Images** | High quality | Optimized size |
| **QR Codes** | Multiple, large | Single, compact |
| **Margins** | 10-15mm | 2-3mm |
| **Line Items** | Wrapped | Truncated |
| **Page Breaks** | Supported | Continuous |
| **Print Speed** | Moderate | Fast |
| **Cost/Page** | Higher | Lower |

## 🔮 Future Enhancements

### Planned Features
- [ ] Custom paper size definition
- [ ] ESC/POS direct commands for thermal
- [ ] Network printer discovery
- [ ] Cloud printing support
- [ ] Email invoice directly
- [ ] Batch printing
- [ ] Custom watermarks
- [ ] Digital signatures
- [ ] Multi-language templates
- [ ] Barcode support

### API Extensions
- REST API for remote printing
- WebSocket for real-time preview
- PDF/A archival format
- Export to Excel/CSV
- Integration with accounting software

## 📚 Related Documentation

- [Dashboard Features](DASHBOARD_FEATURES.md)
- [POS System README](README.md)
- [API Documentation](API_DOCS.md)
- [Database Schema](DATABASE_SCHEMA.md)

---

**Version**: 2.0.0  
**Last Updated**: September 2025  
**Module**: Invoice Generation System  
**License**: MIT
