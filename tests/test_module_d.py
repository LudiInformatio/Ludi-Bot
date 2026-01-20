
import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from module_d import LudiYak

class TestModuleD(unittest.TestCase):
    def setUp(self):
        self.yak = LudiYak()
        
        # Test config mapping (subset of prod config)
        self.test_keywords = {
            "categories": {
                "INJURY_OUT": {
                    "keywords": ["ruled out", "won't play"],
                    "confidence": 1.0, 
                    "status": "OUT"
                },
                "INJURY_GTD": {
                    "keywords": ["questionable", "mri"],
                    "confidence": 0.8,
                    "status": "GTD"
                },
                "PERFORMANCE": {
                    "keywords": ["pours in", "scores"],
                    "filter": "SKIP"
                }
            }
        }
        
    def test_classify_headline_out(self):
        """Test classifying an OUT headline."""
        self.yak.keywords_config = self.test_keywords
        text = "Jimmy Butler: Ruled out for Monday's game"
        
        result = self.yak.classify_headline(text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'OUT')
        self.assertEqual(result['category'], 'INJURY_OUT')
        self.assertEqual(result['confidence'], 1.0)
        
    def test_classify_headline_gtd(self):
        """Test classifying a Questionable/GTD headline."""
        self.yak.keywords_config = self.test_keywords
        text = "Jimmy Butler: Questionable with knee soreness"
        
        result = self.yak.classify_headline(text)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'GTD')
        self.assertEqual(result['category'], 'INJURY_GTD')
        
    def test_classify_headline_skip(self):
        """Test that performance headlines are skipped."""
        self.yak.keywords_config = self.test_keywords
        text = "Jalen Brunson: Pours in 40 points in win"
        
        result = self.yak.classify_headline(text)
        
        self.assertIsNone(result)
        
    def test_get_refresh_interval(self):
        """Test dynamic refresh interval logic."""
        # Mock datetime to test time windows
        with patch('module_d.datetime') as mock_date:
            with patch('module_d.pytz') as mock_pytz:
                # Mock timezone setup
                mock_est = MagicMock()
                mock_pytz.timezone.return_value = mock_est
                
                # Test 2 PM (Day -> 20 min)
                mock_now = MagicMock()
                mock_now.hour = 14
                mock_date.now.return_value = mock_now
                self.assertEqual(self.yak.get_refresh_interval(), 20)
                
                # Test 7 PM (Game Time -> 10 min)
                mock_now.hour = 19
                mock_date.now.return_value = mock_now
                self.assertEqual(self.yak.get_refresh_interval(), 10)
                
                # Test 4 AM (Off Hours -> 30 min)
                mock_now.hour = 4
                mock_date.now.return_value = mock_now
                self.assertEqual(self.yak.get_refresh_interval(), 30)

if __name__ == '__main__':
    unittest.main()
