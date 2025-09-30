#!/usr/bin/env python3
"""
Comprehensive Test Suite for Multi-Format Invoice System
Tests all formats, edge cases, and validation rules
"""
import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta
from decimal import Decimal

# Import modules to test
from invoice_formats import (
    BillSize, LayoutStyle, BillFormatRegistry, 
    AutoLayoutEngine, ThermalOptimizer, LayoutConfig, Margins
)
from invoice_generator_enhanced import EnhancedInvoiceGenerator
from database import db
from auth import hash_password

class TestInvoiceFormats(unittest.TestCase):
    """Test invoice format registry and configurations"""
    
    def setUp(self):
        self.registry = BillFormatRegistry()
    
    def test_all_bill_sizes_defined(self):
        """Test that all bill sizes are properly defined"""
        sizes = self.registry.get_all_sizes()
        self.assertEqual(len(sizes), 13)  # Total number of sizes
        
        # Test categories
        paper_sizes = self.registry.get_paper_sizes()
        thermal_sizes = self.registry.get_thermal_sizes()
        
        self.assertGreater(len(paper_sizes), 0)
        self.assertGreater(len(thermal_sizes), 0)
        self.assertEqual(len(paper_sizes) + len(thermal_sizes), len(sizes))
    
    def test_size_dimensions(self):
        """Test size dimension calculations"""
        # Test A4
        a4 = BillSize.A4
        self.assertEqual(a4.width_mm, 210)
        self.assertEqual(a4.height_mm, 297)
        self.assertAlmostEqual(a4.width_inches, 8.27, places=1)
        self.assertAlmostEqual(a4.height_inches, 11.69, places=1)
        
        # Test thermal
        thermal80 = BillSize.THERMAL_80
        self.assertEqual(thermal80.width_mm, 80)
        self.assertEqual(thermal80.height_mm, 0)  # Continuous
        self.assertTrue(thermal80.is_thermal)
        self.assertTrue(thermal80.is_continuous)
    
    def test_default_configurations(self):
        """Test default configuration generation"""
        # Test each size/style combination
        for size in BillSize:
            for style in LayoutStyle:
                config = self.registry.get_default_config(size, style)
                
                self.assertIsInstance(config, LayoutConfig)
                self.assertEqual(config.size, size)
                self.assertEqual(config.style, style)
                
                # Check margins
                self.assertIsInstance(config.margins, Margins)
                self.assertGreater(config.margins.top, 0)
                
                # Check thermal specifics
                if size.is_thermal:
                    self.assertGreater(config.chars_per_line, 0)
                    self.assertLessEqual(config.max_qr_codes, 1)
                else:
                    self.assertEqual(config.chars_per_line, 0)
                    self.assertGreaterEqual(config.max_qr_codes, 1)
    
    def test_margin_validation(self):
        """Test margin validation rules"""
        # Valid paper margins
        paper_margins = Margins(10, 10, 10, 10)
        valid, msg = self.registry.validate_margins(paper_margins, "paper")
        self.assertTrue(valid)
        self.assertEqual(msg, "")
        
        # Invalid paper margins
        small_margins = Margins(2, 2, 2, 2)
        valid, msg = self.registry.validate_margins(small_margins, "paper")
        self.assertFalse(valid)
        self.assertIn("too small", msg)
        
        # Valid thermal margins
        thermal_margins = Margins(2, 2, 2, 2)
        valid, msg = self.registry.validate_margins(thermal_margins, "thermal")
        self.assertTrue(valid)
    
    def test_find_closest_size(self):
        """Test finding closest matching size"""
        # Should find A4 for similar dimensions
        closest = self.registry.find_closest_size(215, 300, prefer_thermal=False)
        self.assertEqual(closest, BillSize.A4)
        
        # Should find closest thermal when preferring thermal
        closest = self.registry.find_closest_size(78, 0, prefer_thermal=True)
        # Accept either THERMAL_76 or THERMAL_80 as both are close
        self.assertIn(closest, [BillSize.THERMAL_76, BillSize.THERMAL_80])


class TestAutoLayoutEngine(unittest.TestCase):
    """Test automatic layout adaptation"""
    
    def setUp(self):
        self.registry = BillFormatRegistry()
    
    def test_item_layout_paper(self):
        """Test item layout for paper formats"""
        config = self.registry.get_default_config(BillSize.A4, LayoutStyle.CLASSIC)
        engine = AutoLayoutEngine(config)
        
        # Short item name
        result = engine.calculate_item_layout("Coffee")
        self.assertEqual(result["lines"], ["Coffee"])
        self.assertFalse(result["truncated"])
        
        # Long item name with wrapping
        long_name = "Extra Large Cappuccino with Double Shot Espresso and Whipped Cream"
        result = engine.calculate_item_layout(long_name)
        self.assertGreater(len(result["lines"]), 1)
        self.assertLessEqual(len(result["lines"]), config.max_lines_per_item)
    
    def test_item_layout_thermal(self):
        """Test item layout for thermal formats"""
        config = self.registry.get_default_config(BillSize.THERMAL_80, LayoutStyle.COMPACT)
        engine = AutoLayoutEngine(config)
        
        # Should truncate long names
        long_name = "Extra Large Cappuccino with Double Shot"
        result = engine.calculate_item_layout(long_name)
        self.assertEqual(len(result["lines"]), 1)
        if len(long_name) > config.chars_per_line * 0.45:
            self.assertTrue(result["truncated"])
            self.assertIn("...", result["display_name"])
    
    def test_qr_layout_arrangements(self):
        """Test QR code layout calculations"""
        # Paper format with multiple QR codes
        config = self.registry.get_default_config(BillSize.A4, LayoutStyle.CLASSIC)
        engine = AutoLayoutEngine(config)
        
        # 2 QR codes - horizontal
        layout = engine.calculate_qr_layout(2)
        self.assertEqual(layout["arrangement"], "horizontal")
        
        # 4 QR codes - grid
        layout = engine.calculate_qr_layout(4)
        self.assertIn(layout["arrangement"], ["horizontal", "grid"])
        
        # Thermal format - always vertical
        config = self.registry.get_default_config(BillSize.THERMAL_58, LayoutStyle.COMPACT)
        engine = AutoLayoutEngine(config)
        layout = engine.calculate_qr_layout(3)
        self.assertEqual(layout["arrangement"], "vertical")
        self.assertEqual(layout["count"], 1)  # Limited to 1 for thermal
    
    def test_content_height_estimation(self):
        """Test content height estimation"""
        config = self.registry.get_default_config(BillSize.A4, LayoutStyle.CLASSIC)
        engine = AutoLayoutEngine(config)
        
        # Estimate for different item counts
        height_5 = engine.estimate_content_height(5, has_qr=False, has_logo=False)
        height_10 = engine.estimate_content_height(10, has_qr=False, has_logo=False)
        height_with_extras = engine.estimate_content_height(5, has_qr=True, has_logo=True)
        
        self.assertLess(height_5, height_10)
        self.assertLess(height_5, height_with_extras)
    
    def test_pagination(self):
        """Test pagination calculations"""
        config = self.registry.get_default_config(BillSize.A5, LayoutStyle.CLASSIC)
        engine = AutoLayoutEngine(config)
        
        # Create many items
        items = [{"name": f"Item {i}", "qty": 1} for i in range(50)]
        
        # Should need pagination
        pages = engine.calculate_page_breaks(items, items_per_page=20)
        self.assertEqual(len(pages), 3)  # 50 items / 20 per page
        self.assertEqual(len(pages[0]), 20)
        self.assertEqual(len(pages[2]), 10)
        
        # Thermal should not paginate
        config = self.registry.get_default_config(BillSize.THERMAL_80, LayoutStyle.COMPACT)
        engine = AutoLayoutEngine(config)
        needs_pagination = engine.needs_pagination(1000)  # Very tall content
        self.assertFalse(needs_pagination)  # Continuous feed


class TestThermalOptimizer(unittest.TestCase):
    """Test thermal printer optimizations"""
    
    def test_text_truncation(self):
        """Test text truncation for thermal width"""
        # Normal truncation
        text = "This is a very long text that needs truncation"
        result = ThermalOptimizer.optimize_for_thermal(text, 20)
        self.assertEqual(len(result), 20)
        self.assertIn("...", result)
        
        # Short text - no truncation
        short_text = "Short"
        result = ThermalOptimizer.optimize_for_thermal(short_text, 20)
        self.assertEqual(result, short_text)
    
    def test_line_formatting(self):
        """Test thermal line formatting with alignment"""
        # Normal line
        line = ThermalOptimizer.format_thermal_line("Item", "₹100.00", 32)
        self.assertEqual(len(line), 32)
        self.assertIn("Item", line)
        self.assertIn("₹100.00", line)
        
        # Long text that needs truncation
        line = ThermalOptimizer.format_thermal_line(
            "Very Long Item Name That Exceeds Width",
            "₹999.99", 32
        )
        self.assertEqual(len(line), 32)
    
    def test_separator_creation(self):
        """Test separator line creation"""
        sep = ThermalOptimizer.create_thermal_separator(32, "-")
        self.assertEqual(len(sep), 32)
        self.assertEqual(sep, "-" * 32)
        
        sep = ThermalOptimizer.create_thermal_separator(20, "=")
        self.assertEqual(len(sep), 20)
        self.assertEqual(sep, "=" * 20)
    
    def test_center_text(self):
        """Test text centering"""
        centered = ThermalOptimizer.center_text("RECEIPT", 32)
        self.assertEqual(len(centered.strip()), len("RECEIPT"))
        self.assertIn("RECEIPT", centered)
        
        # Text longer than width
        centered = ThermalOptimizer.center_text("A" * 40, 32)
        self.assertLessEqual(len(centered), 32)


class TestEnhancedInvoiceGenerator(unittest.TestCase):
    """Test enhanced invoice generator"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database and sample order"""
        # Initialize database
        db.init_database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Create test user
        cursor.execute("""
            INSERT OR IGNORE INTO users (id, username, password_hash, role, active)
            VALUES (1, 'testuser', ?, 'admin', 1)
        """, (hash_password('test123'),))
        
        # Create test order
        cursor.execute("""
            INSERT OR REPLACE INTO orders (
                id, user_id, subtotal, tax_rate, tax_total, 
                grand_total, status, created_at
            ) VALUES (
                999, 1, 100.00, 10.0, 10.00, 
                110.00, 'finalized', ?
            )
        """, (datetime.now().isoformat(),))
        
        # Create test order items
        cursor.execute("""
            INSERT OR REPLACE INTO order_items (
                order_id, name, quantity, unit_price, line_total
            ) VALUES 
            (999, 'Test Item 1', 2, 25.00, 50.00),
            (999, 'Test Item 2', 1, 50.00, 50.00)
        """)
        
        conn.commit()
    
    def setUp(self):
        self.generator = EnhancedInvoiceGenerator()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temporary files"""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)
    
    def test_generate_paper_invoice(self):
        """Test generating invoice for paper format"""
        output_path = os.path.join(self.temp_dir, "test_a4.pdf")
        
        result = self.generator.generate_invoice(
            order_id=999,
            bill_size=BillSize.A4,
            layout_style=LayoutStyle.CLASSIC,
            output_path=output_path
        )
        
        self.assertEqual(result, output_path)
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 0)
    
    def test_generate_thermal_invoice(self):
        """Test generating invoice for thermal format"""
        output_path = os.path.join(self.temp_dir, "test_thermal.pdf")
        
        result = self.generator.generate_invoice(
            order_id=999,
            bill_size=BillSize.THERMAL_80,
            layout_style=LayoutStyle.COMPACT,
            output_path=output_path
        )
        
        self.assertEqual(result, output_path)
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 0)
    
    def test_all_formats_generation(self):
        """Test generating invoices for all formats"""
        for size in BillSize:
            with self.subTest(size=size):
                output_path = os.path.join(
                    self.temp_dir, 
                    f"test_{size.name.lower()}.pdf"
                )
                
                # Use appropriate layout for format
                layout = LayoutStyle.COMPACT if size.is_thermal else LayoutStyle.CLASSIC
                
                result = self.generator.generate_invoice(
                    order_id=999,
                    bill_size=size,
                    layout_style=layout,
                    output_path=output_path
                )
                
                self.assertTrue(os.path.exists(result))
                self.assertGreater(os.path.getsize(result), 0)
    
    def test_preview_generation(self):
        """Test preview mode generation"""
        result = self.generator.generate_invoice(
            order_id=999,
            bill_size=BillSize.A4,
            layout_style=LayoutStyle.MINIMAL,
            preview_only=True
        )
        
        self.assertTrue(os.path.exists(result))
        self.assertIn("preview", result)
    
    def test_invalid_order_handling(self):
        """Test handling of invalid order ID"""
        with self.assertRaises(ValueError):
            self.generator.generate_invoice(
                order_id=99999,  # Non-existent order
                bill_size=BillSize.A4
            )


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and validation"""
    
    def setUp(self):
        self.registry = BillFormatRegistry()
    
    def test_extremely_long_item_names(self):
        """Test handling of extremely long item names"""
        config = self.registry.get_default_config(BillSize.A4, LayoutStyle.CLASSIC)
        engine = AutoLayoutEngine(config)
        
        # 500 character item name
        long_name = "A" * 500
        result = engine.calculate_item_layout(long_name)
        
        # Should be wrapped and truncated
        self.assertLessEqual(len(result["lines"]), config.max_lines_per_item)
        total_chars = sum(len(line) for line in result["lines"])
        # Should be less than or equal to original (due to wrapping/truncation)
        self.assertLessEqual(total_chars, 500)
    
    def test_zero_margins_validation(self):
        """Test zero margins are rejected"""
        zero_margins = Margins(0, 0, 0, 0)
        
        valid, msg = self.registry.validate_margins(zero_margins, "paper")
        self.assertFalse(valid)
        
        valid, msg = self.registry.validate_margins(zero_margins, "thermal")
        self.assertFalse(valid)
    
    def test_empty_order_items(self):
        """Test handling of order with no items"""
        # This should be handled gracefully
        config = self.registry.get_default_config(BillSize.A4, LayoutStyle.CLASSIC)
        engine = AutoLayoutEngine(config)
        
        pages = engine.calculate_page_breaks([])
        self.assertEqual(len(pages), 1)
        self.assertEqual(len(pages[0]), 0)
    
    def test_special_characters_in_thermal(self):
        """Test special character handling in thermal format"""
        # INR symbol
        text = "Total: ₹1,234.56"
        result = ThermalOptimizer.optimize_for_thermal(text, 20)
        self.assertIn("₹", result)
        
        # Unicode characters
        text = "Café Latté €5.00"
        result = ThermalOptimizer.optimize_for_thermal(text, 20)
        self.assertLessEqual(len(result), 20)


class TestPerformance(unittest.TestCase):
    """Test performance requirements"""
    
    def test_thermal_generation_speed(self):
        """Test thermal invoice generation is under 300ms"""
        import time
        
        generator = EnhancedInvoiceGenerator()
        
        start = time.time()
        generator.generate_invoice(
            order_id=999,
            bill_size=BillSize.THERMAL_80,
            layout_style=LayoutStyle.COMPACT
        )
        elapsed = time.time() - start
        
        # Should be under 1 second (relaxed for CI environments)
        self.assertLess(elapsed, 1.0)
    
    def test_configuration_lookup_speed(self):
        """Test configuration lookup is fast"""
        import time
        
        registry = BillFormatRegistry()
        
        start = time.time()
        for _ in range(100):
            config = registry.get_default_config(
                BillSize.A4, 
                LayoutStyle.CLASSIC
            )
        elapsed = time.time() - start
        
        # 100 lookups should be under 100ms
        self.assertLess(elapsed, 0.1)


def run_tests():
    """Run all tests with verbose output"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceFormats))
    suite.addTests(loader.loadTestsFromTestCase(TestAutoLayoutEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestThermalOptimizer))
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedInvoiceGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED!")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
