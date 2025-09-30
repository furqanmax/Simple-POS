"""
Invoice Format Registry and Auto-Layout Engine
Comprehensive support for multiple paper and thermal formats with automatic layout adaptation
"""
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import math

class BillSize(Enum):
    """Supported bill sizes with dimensions in mm"""
    # A-series paper
    A5 = ("A5", 148, 210, "paper")
    A4 = ("A4", 210, 297, "paper")
    A3 = ("A3", 297, 420, "paper")
    
    # North American sizes (converted to mm)
    HALF_LETTER = ("Half Letter", 140, 216, "paper")  # 5.5 × 8.5 in
    LETTER = ("Letter", 216, 279, "paper")  # 8.5 × 11 in
    LEGAL = ("Legal", 216, 356, "paper")  # 8.5 × 14 in
    
    # Receipt/thermal roll widths
    THERMAL_57 = ("57mm Thermal", 57, 0, "thermal")  # Narrow thermal
    THERMAL_58 = ("58mm Thermal", 58, 0, "thermal")  # Standard compact
    THERMAL_76 = ("76mm Thermal", 76, 0, "thermal")  # Medium thermal
    THERMAL_80 = ("80mm Thermal", 80, 0, "thermal")  # Standard thermal
    
    # Pad/strip formats
    QUARTER_LETTER = ("¼-Letter Strip", 108, 216, "paper")  # 4.25 × 8.5 in
    LONG_STRIP = ("Long Strip", 70, 194, "paper")  # 2.75 × 7.625 in
    CASH_RECEIPT = ("Cash Receipt", 109, 189, "paper")  # 10.9 × 18.9 cm
    
    def __init__(self, display_name, width_mm, height_mm, category):
        self.display_name = display_name
        self.width_mm = width_mm
        self.height_mm = height_mm  # 0 for continuous thermal
        self.category = category
    
    @property
    def width_inches(self):
        return self.width_mm / 25.4
    
    @property
    def height_inches(self):
        return self.height_mm / 25.4 if self.height_mm > 0 else 0
    
    @property
    def is_thermal(self):
        return self.category == "thermal"
    
    @property
    def is_continuous(self):
        return self.height_mm == 0


class LayoutStyle(Enum):
    """Invoice layout styles"""
    CLASSIC = "classic"  # Traditional layout with full details
    MINIMAL = "minimal"  # Clean, minimal design
    COMPACT = "compact"  # Optimized for thermal printers
    DETAILED = "detailed"  # Maximum information density


@dataclass
class Margins:
    """Margin settings for a format"""
    top: float
    right: float
    bottom: float
    left: float
    
    @property
    def horizontal_total(self):
        return self.left + self.right
    
    @property
    def vertical_total(self):
        return self.top + self.bottom


@dataclass
class FontSettings:
    """Font configuration for different elements"""
    base_size: int
    title_size: int
    header_size: int
    item_size: int
    footer_size: int
    mono_font: str = "Courier"
    sans_font: str = "Helvetica"
    
    def scale(self, factor: float):
        """Scale all font sizes by a factor"""
        return FontSettings(
            base_size=int(self.base_size * factor),
            title_size=int(self.title_size * factor),
            header_size=int(self.header_size * factor),
            item_size=int(self.item_size * factor),
            footer_size=int(self.footer_size * factor),
            mono_font=self.mono_font,
            sans_font=self.sans_font
        )


@dataclass
class LayoutConfig:
    """Complete layout configuration for a size/style combination"""
    size: BillSize
    style: LayoutStyle
    margins: Margins
    fonts: FontSettings
    chars_per_line: int  # For thermal printers
    max_qr_codes: int
    qr_size_mm: float
    logo_max_height_mm: float
    show_borders: bool
    column_widths: Dict[str, float]  # Percentage widths for table columns
    wrap_item_names: bool
    max_lines_per_item: int
    page_break_threshold: float  # Percentage of page before break
    
    @property
    def printable_width_mm(self):
        return self.size.width_mm - self.margins.horizontal_total
    
    @property
    def printable_height_mm(self):
        if self.size.is_continuous:
            return 0
        return self.size.height_mm - self.margins.vertical_total


class BillFormatRegistry:
    """Registry of all supported bill formats with their configurations"""
    
    # Default margins per category (in mm)
    DEFAULT_MARGINS = {
        "paper": {
            "large": Margins(15, 15, 15, 15),  # A3, Letter, Legal
            "medium": Margins(12, 12, 12, 12),  # A4
            "small": Margins(10, 10, 10, 10),  # A5, Half-letter
            "strip": Margins(5, 5, 5, 5)  # Strips
        },
        "thermal": {
            "standard": Margins(3, 3, 3, 3),
            "minimal": Margins(2, 2, 2, 2)
        }
    }
    
    # Minimum margins to prevent clipping (in mm)
    MIN_MARGINS = {
        "paper": Margins(5, 5, 5, 5),
        "thermal": Margins(2, 2, 2, 2)
    }
    
    # Font scaling factors based on size
    FONT_SCALES = {
        BillSize.A3: 1.2,
        BillSize.A4: 1.0,
        BillSize.A5: 0.85,
        BillSize.LETTER: 1.0,
        BillSize.LEGAL: 1.0,
        BillSize.HALF_LETTER: 0.85,
        BillSize.THERMAL_80: 0.8,
        BillSize.THERMAL_76: 0.75,
        BillSize.THERMAL_58: 0.7,
        BillSize.THERMAL_57: 0.7,
        BillSize.QUARTER_LETTER: 0.8,
        BillSize.LONG_STRIP: 0.75,
        BillSize.CASH_RECEIPT: 0.8
    }
    
    @classmethod
    def get_default_config(cls, size: BillSize, style: LayoutStyle) -> LayoutConfig:
        """Get default configuration for a size/style combination"""
        
        # Determine margins
        if size.is_thermal:
            margins = cls.DEFAULT_MARGINS["thermal"]["minimal" if style == LayoutStyle.COMPACT else "standard"]
        else:
            if size in [BillSize.A3, BillSize.LETTER, BillSize.LEGAL]:
                margins = cls.DEFAULT_MARGINS["paper"]["large"]
            elif size in [BillSize.A4]:
                margins = cls.DEFAULT_MARGINS["paper"]["medium"]
            elif size in [BillSize.A5, BillSize.HALF_LETTER]:
                margins = cls.DEFAULT_MARGINS["paper"]["small"]
            else:
                margins = cls.DEFAULT_MARGINS["paper"]["strip"]
        
        # Base font settings
        base_fonts = FontSettings(
            base_size=10,
            title_size=16,
            header_size=12,
            item_size=9,
            footer_size=8
        )
        
        # Scale fonts based on size
        scale_factor = cls.FONT_SCALES.get(size, 1.0)
        fonts = base_fonts.scale(scale_factor)
        
        # Calculate characters per line for thermal
        chars_per_line = 0
        if size.is_thermal:
            # Assuming 12 chars per inch for standard thermal font
            printable_width = size.width_mm - margins.horizontal_total
            chars_per_line = int(printable_width / 2.5)  # ~2.5mm per character
        
        # QR code settings
        max_qr_codes = 1 if size.is_thermal else (3 if size in [BillSize.A3, BillSize.LETTER, BillSize.LEGAL] else 2)
        qr_size_mm = 15 if size.is_thermal else (25 if size in [BillSize.A3] else 20)
        
        # Logo settings
        logo_max_height = 15 if size.is_thermal else (30 if size in [BillSize.A3] else 25)
        
        # Column widths (percentages)
        if style == LayoutStyle.COMPACT or size.is_thermal:
            column_widths = {
                "item": 0.45,
                "qty": 0.15,
                "price": 0.20,
                "total": 0.20
            }
        elif style == LayoutStyle.DETAILED:
            column_widths = {
                "item": 0.35,
                "description": 0.25,
                "qty": 0.10,
                "price": 0.15,
                "total": 0.15
            }
        else:  # Classic or Minimal
            column_widths = {
                "item": 0.40,
                "qty": 0.15,
                "price": 0.20,
                "total": 0.25
            }
        
        return LayoutConfig(
            size=size,
            style=style,
            margins=margins,
            fonts=fonts,
            chars_per_line=chars_per_line,
            max_qr_codes=max_qr_codes,
            qr_size_mm=qr_size_mm,
            logo_max_height_mm=logo_max_height,
            show_borders=(style != LayoutStyle.MINIMAL),
            column_widths=column_widths,
            wrap_item_names=(not size.is_thermal),
            max_lines_per_item=(1 if size.is_thermal else 3),
            page_break_threshold=0.85
        )
    
    @classmethod
    def validate_margins(cls, margins: Margins, category: str) -> Tuple[bool, str]:
        """Validate margins against minimum requirements"""
        min_margins = cls.MIN_MARGINS.get(category, cls.MIN_MARGINS["paper"])
        
        errors = []
        if margins.top < min_margins.top:
            errors.append(f"Top margin too small (min: {min_margins.top}mm)")
        if margins.right < min_margins.right:
            errors.append(f"Right margin too small (min: {min_margins.right}mm)")
        if margins.bottom < min_margins.bottom:
            errors.append(f"Bottom margin too small (min: {min_margins.bottom}mm)")
        if margins.left < min_margins.left:
            errors.append(f"Left margin too small (min: {min_margins.left}mm)")
        
        if errors:
            return False, "; ".join(errors)
        return True, ""
    
    @classmethod
    def get_all_sizes(cls) -> List[BillSize]:
        """Get all supported bill sizes"""
        return list(BillSize)
    
    @classmethod
    def get_paper_sizes(cls) -> List[BillSize]:
        """Get only paper sizes"""
        return [s for s in BillSize if not s.is_thermal]
    
    @classmethod
    def get_thermal_sizes(cls) -> List[BillSize]:
        """Get only thermal sizes"""
        return [s for s in BillSize if s.is_thermal]
    
    @classmethod
    def find_closest_size(cls, width_mm: float, height_mm: float, 
                         prefer_thermal: bool = False) -> Optional[BillSize]:
        """Find the closest matching size for given dimensions"""
        sizes = cls.get_thermal_sizes() if prefer_thermal else cls.get_paper_sizes()
        
        if not sizes:
            sizes = cls.get_all_sizes()
        
        best_match = None
        min_diff = float('inf')
        
        for size in sizes:
            if size.is_continuous:
                # For continuous formats, only compare width
                diff = abs(size.width_mm - width_mm)
            else:
                # For fixed formats, compare both dimensions
                diff = math.sqrt((size.width_mm - width_mm)**2 + 
                               (size.height_mm - height_mm)**2)
            
            if diff < min_diff:
                min_diff = diff
                best_match = size
        
        return best_match


class AutoLayoutEngine:
    """Automatic layout engine that adapts content to different formats"""
    
    def __init__(self, config: LayoutConfig):
        self.config = config
    
    def calculate_item_layout(self, item_name: str) -> Dict[str, Any]:
        """Calculate layout for a single item based on format constraints"""
        result = {
            "display_name": item_name,
            "lines": [],
            "truncated": False
        }
        
        if self.config.size.is_thermal:
            # For thermal, truncate or wrap based on character limit
            if len(item_name) > self.config.chars_per_line * 0.45:  # Item column width
                max_chars = int(self.config.chars_per_line * 0.45 - 3)
                result["display_name"] = item_name[:max_chars] + "..."
                result["truncated"] = True
            result["lines"] = [result["display_name"]]
        else:
            # For paper, allow wrapping
            if self.config.wrap_item_names:
                # Simple word wrapping (can be enhanced)
                words = item_name.split()
                lines = []
                current_line = []
                
                for word in words:
                    if len(" ".join(current_line + [word])) <= 40:  # Approximate
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(" ".join(current_line))
                        current_line = [word]
                
                if current_line:
                    lines.append(" ".join(current_line))
                
                # Limit lines
                if len(lines) > self.config.max_lines_per_item:
                    lines = lines[:self.config.max_lines_per_item]
                    lines[-1] = lines[-1][:-3] + "..."
                    result["truncated"] = True
                
                result["lines"] = lines
            else:
                result["lines"] = [item_name]
        
        return result
    
    def calculate_qr_layout(self, num_qr_codes: int) -> Dict[str, Any]:
        """Calculate optimal QR code placement"""
        max_qr = self.config.max_qr_codes
        actual_count = min(num_qr_codes, max_qr)
        
        if self.config.size.is_thermal:
            # Vertical stacking for thermal
            return {
                "count": actual_count,
                "arrangement": "vertical",
                "size_mm": self.config.qr_size_mm,
                "spacing_mm": 2
            }
        else:
            # Grid arrangement for paper
            if actual_count <= 2:
                return {
                    "count": actual_count,
                    "arrangement": "horizontal",
                    "size_mm": self.config.qr_size_mm,
                    "spacing_mm": 5
                }
            else:
                # 2x2 grid for 3-4 QR codes
                return {
                    "count": actual_count,
                    "arrangement": "grid",
                    "rows": 2,
                    "cols": 2,
                    "size_mm": self.config.qr_size_mm * 0.8,  # Slightly smaller
                    "spacing_mm": 5
                }
    
    def estimate_content_height(self, num_items: int, has_qr: bool, 
                               has_logo: bool) -> float:
        """Estimate total content height in mm"""
        height = 0
        
        # Header with logo
        if has_logo:
            height += self.config.logo_max_height_mm + 5
        
        # Business info
        height += 30  # Approximate
        
        # Invoice info
        height += 20
        
        # Items table
        item_row_height = 5 if self.config.size.is_thermal else 7
        height += (num_items + 1) * item_row_height  # +1 for header
        
        # Totals
        height += 20
        
        # QR codes
        if has_qr:
            height += self.config.qr_size_mm + 10
        
        # Footer
        height += 15
        
        return height
    
    def needs_pagination(self, content_height_mm: float) -> bool:
        """Check if content needs pagination"""
        if self.config.size.is_continuous:
            return False  # Continuous feed doesn't need pagination
        
        available_height = self.config.printable_height_mm
        threshold_height = available_height * self.config.page_break_threshold
        
        return content_height_mm > threshold_height
    
    def calculate_page_breaks(self, items: List[Dict], 
                            items_per_page: Optional[int] = None) -> List[List[Dict]]:
        """Calculate optimal page breaks for items"""
        if not self.needs_pagination(self.estimate_content_height(len(items), False, False)):
            return [items]
        
        # Calculate items per page
        if not items_per_page:
            # Estimate based on available height
            available_height = self.config.printable_height_mm * 0.6  # Reserve space for headers/footers
            item_height = 5 if self.config.size.is_thermal else 7
            items_per_page = int(available_height / item_height)
        
        # Split items into pages
        pages = []
        for i in range(0, len(items), items_per_page):
            pages.append(items[i:i + items_per_page])
        
        return pages


class ThermalOptimizer:
    """Optimization specifically for thermal printers"""
    
    @staticmethod
    def optimize_for_thermal(text: str, width_chars: int) -> str:
        """Optimize text for thermal printer width"""
        if len(text) <= width_chars:
            return text
        
        # Try to intelligently truncate
        if width_chars > 3:
            return text[:width_chars-3] + "..."
        return text[:width_chars]
    
    @staticmethod
    def format_thermal_line(left: str, right: str, width: int) -> str:
        """Format a line with left and right alignment for thermal"""
        padding = width - len(left) - len(right)
        if padding < 0:
            # Need to truncate
            available = width - 3
            left_chars = int(available * 0.6)
            right_chars = available - left_chars
            left = ThermalOptimizer.optimize_for_thermal(left, left_chars)
            right = ThermalOptimizer.optimize_for_thermal(right, right_chars)
            padding = width - len(left) - len(right)
        
        return left + " " * max(padding, 1) + right
    
    @staticmethod
    def create_thermal_separator(width: int, char: str = "-") -> str:
        """Create a separator line for thermal printer"""
        return char * width
    
    @staticmethod
    def center_text(text: str, width: int) -> str:
        """Center text within given width"""
        if len(text) >= width:
            return ThermalOptimizer.optimize_for_thermal(text, width)
        padding = (width - len(text)) // 2
        return " " * padding + text
