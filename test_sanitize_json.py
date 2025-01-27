import unittest
from utils.json_sanitizer import sanitize_json

class TestSanitizeJson(unittest.TestCase):
    def test_sanitize_simple(self):
        self.assertEqual(sanitize_json({"value": float('nan')}), {"value": None})
    
    def test_sanitize_nested(self):
        data = {"outer": {"inner": float('nan')}}
        expected = {"outer": {"inner": None}}
        self.assertEqual(sanitize_json(data), expected)
    
    def test_sanitize_list(self):
        data = [1, float('nan'), 3]
        expected = [1, None, 3]
        self.assertEqual(sanitize_json(data), expected)
    
    def test_sanitize_mixed(self):
        data = {"numbers": [1, 2, float('nan')], "value": float('nan')}
        expected = {"numbers": [1, 2, None], "value": None}
        self.assertEqual(sanitize_json(data), expected)

if __name__ == "__main__":
    unittest.main() 