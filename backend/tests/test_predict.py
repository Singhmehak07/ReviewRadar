import unittest
import sys
import os

# Add root directory to path to ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.predict import predict_review, clean_text, assign_risk_band

class TestPredictReview(unittest.TestCase):
    def setUp(self):
        self.expected_disclaimer = "Highlights suspicious review patterns; does not prove fraud."
        self.allowed_risk_bands = {"Low", "Moderate", "High"}

    def verify_schema(self, result):
        """Helper to assert that the output complies with the expected schema."""
        self.assertIsInstance(result, dict)
        self.assertIn("risk_score", result)
        self.assertIn("risk_band", result)
        self.assertIn("disclaimer", result)
        
        score = result["risk_score"]
        band = result["risk_band"]
        disclaimer = result["disclaimer"]
        
        self.assertIsInstance(score, float)
        self.assertTrue(0.0 <= score <= 100.0, f"Score {score} is out of bounds [0, 100]")
        self.assertIn(band, self.allowed_risk_bands)
        self.assertEqual(disclaimer, self.expected_disclaimer)

        # Verify correct risk band mapping
        if score < 40:
            self.assertEqual(band, "Low")
        elif score < 70:
            self.assertEqual(band, "Moderate")
        else:
            self.assertEqual(band, "High")

    def test_standard_inputs(self):
        # Normal positive/negative review
        res_pos = predict_review("This is an absolutely amazing product, highly recommend!")
        self.verify_schema(res_pos)
        
        res_neg = predict_review("Terrible product. Broke on day one. Extremely disappointed.")
        self.verify_schema(res_neg)

    def test_empty_string(self):
        res = predict_review("")
        self.verify_schema(res)

    def test_whitespace_only(self):
        res = predict_review("     \n\t   ")
        self.verify_schema(res)

    def test_very_long_text(self):
        long_text = "This is a repeated phrase. " * 5000  # 130,000 characters
        res = predict_review(long_text)
        self.verify_schema(res)

    def test_html_only(self):
        res = predict_review("<div><p><span></span></p></div>")
        self.verify_schema(res)

    def test_url_only(self):
        res = predict_review("http://some-fake-url.com/path?query=1&var=2 www.test.org")
        self.verify_schema(res)

    def test_special_characters(self):
        res = predict_review("!@#$%^&*()_+=-[]{}|;':\",./<>?~`\\")
        self.verify_schema(res)

    def test_non_english_text(self):
        res = predict_review("Ce produit est absolument fantastique et merveilleux. Je l'adore!")
        self.verify_schema(res)
        
        res_utf8 = predict_review("这是一个非常好的产品，我非常喜欢。")
        self.verify_schema(res_utf8)

    def test_emoji_only(self):
        res = predict_review("⭐⭐⭐⭐⭐ 😍🔥👍")
        self.verify_schema(res)

    def test_none_input(self):
        res = predict_review(None)
        self.verify_schema(res)

    def test_numeric_input(self):
        res = predict_review(1234567890)
        self.verify_schema(res)

    def test_clean_text_edge_cases(self):
        # Verify cleaning logic
        self.assertEqual(clean_text("<p>Hello <a href='http://x.com'>world</a></p>"), "hello world")
        self.assertEqual(clean_text("   multiple      spaces    "), "multiple spaces")
        self.assertEqual(clean_text(""), "")

if __name__ == "__main__":
    unittest.main()
