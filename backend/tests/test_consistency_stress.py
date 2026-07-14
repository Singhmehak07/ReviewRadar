import unittest
import sys
import os
import re
import time
from backend.signals.consistency import clean_text_for_sentiment, get_consistency_flag, get_analyzer

class TestConsistencyStress(unittest.TestCase):
    def test_html_cleaning_edge_cases(self):
        # Normal tags
        self.assertEqual(clean_text_for_sentiment("<p>Hello</p>"), "Hello")
        # Nested tags
        self.assertEqual(clean_text_for_sentiment("<div><p>Hello <b>World</b></p></div>"), "Hello World")
        # Unclosed tag
        self.assertEqual(clean_text_for_sentiment("<p Hello"), "<p Hello")
        # Comparison operator (less/greater than) - behaves as bug due to regex pattern
        # "a < b and c > d" will match "< b and c >" as a tag and remove it
        self.assertEqual(clean_text_for_sentiment("a < b and c > d"), "a d")
        # Multiple script-like tags
        self.assertEqual(clean_text_for_sentiment("<script>alert(1)</script>"), "alert(1)")
        # Empty tag
        self.assertEqual(clean_text_for_sentiment("<>"), "<>")

    def test_url_cleaning_edge_cases(self):
        # Normal http/https/www
        self.assertEqual(clean_text_for_sentiment("Visit http://example.com for info"), "Visit for info")
        self.assertEqual(clean_text_for_sentiment("Visit https://example.com/a/b?c=1 for info"), "Visit for info")
        self.assertEqual(clean_text_for_sentiment("Visit www.example.com for info"), "Visit for info")
        # ftp URL (not matched by current regex)
        self.assertEqual(clean_text_for_sentiment("ftp://example.com"), "ftp://example.com")
        # Punctuation attached to URL is stripped by \S+
        self.assertEqual(clean_text_for_sentiment("Go to http://example.com, please"), "Go to please")
        self.assertEqual(clean_text_for_sentiment("Go to http://example.com."), "Go to")

    def test_non_string_inputs(self):
        # None input
        self.assertEqual(clean_text_for_sentiment(None), "")
        # Numeric inputs
        self.assertEqual(clean_text_for_sentiment(12345), "12345")
        self.assertEqual(clean_text_for_sentiment(12.34), "12.34")
        # List/Dict inputs
        self.assertEqual(clean_text_for_sentiment([1, 2]), "[1, 2]")
        self.assertEqual(clean_text_for_sentiment({"key": "val"}), "{'key': 'val'}")

    def test_empty_and_whitespace_after_cleaning(self):
        # Initially non-empty but becomes empty after stripping tags
        self.assertEqual(get_consistency_flag("<p></p>", 5), "no_text")
        self.assertEqual(get_consistency_flag("   <p>   </p>   ", 5), "no_text")
        # URL only
        self.assertEqual(get_consistency_flag("http://example.com www.test.com", 5), "no_text")
        # None text
        self.assertEqual(get_consistency_flag(None, 5), "no_text")

    def test_rating_type_and_bounds(self):
        # Float ratings
        # compound = 0.5 (positive)
        # Rating 3.5: rating >= 4 is False, rating <= 2 is False, so it's consistent
        self.assertEqual(get_consistency_flag("This is absolutely wonderful and great!", 3.5), "consistent")
        
        # Rating out of bounds (e.g. 6)
        # compound = -0.5 (negative)
        # Rating 6: rating >= 4 is True, so it's a contradiction
        self.assertEqual(get_consistency_flag("This is terrible, awful, and bad.", 6), "contradiction")
        
        # Rating out of bounds (e.g. 0)
        # compound = 0.5 (positive)
        # Rating 0: rating <= 2 is True, so it's a contradiction
        self.assertEqual(get_consistency_flag("This is absolutely wonderful and great!", 0), "contradiction")

        # Non-numeric ratings (should raise TypeError because of comparison operator)
        with self.assertRaises(TypeError):
            get_consistency_flag("This is great!", "5")
        with self.assertRaises(TypeError):
            get_consistency_flag("This is great!", None)

    def test_vader_boundary_cases(self):
        # We want to check behavior around the exact compound score of -0.3 and 0.3.
        # Let's see what scores are returned by VADER for specific texts, or we can mock polarity_scores.
        # But wait, we can also test using actual mock if needed, or check real text scores.
        analyzer = get_analyzer()
        
        # Find or construct text that has neutral, positive, and negative compounds.
        # "okay" -> compound: 0.2235
        score_okay = analyzer.polarity_scores("okay")["compound"]
        self.assertTrue(-0.3 < score_okay < 0.3)
        self.assertEqual(get_consistency_flag("okay", 5), "neutral_text")
        self.assertEqual(get_consistency_flag("okay", 1), "neutral_text")
        
        # "bad" -> compound: -0.5423
        score_bad = analyzer.polarity_scores("bad")["compound"]
        self.assertTrue(score_bad <= -0.3)
        self.assertEqual(get_consistency_flag("bad", 5), "contradiction")
        self.assertEqual(get_consistency_flag("bad", 1), "consistent")

        # "good" -> compound: 0.4404
        score_good = analyzer.polarity_scores("good")["compound"]
        self.assertTrue(score_good >= 0.3)
        self.assertEqual(get_consistency_flag("good", 5), "consistent")
        self.assertEqual(get_consistency_flag("good", 1), "contradiction")

    def test_performance_stress(self):
        # Large inputs
        large_text = "This is a great product! " * 10000  # ~240,000 chars
        start_time = time.time()
        flag = get_consistency_flag(large_text, 5)
        duration = time.time() - start_time
        self.assertEqual(flag, "consistent")
        # Ensure it runs reasonably quickly (e.g. less than 1.0 second)
        self.assertLess(duration, 1.0, f"Took too long: {duration}s")

        # Extremely large inputs
        huge_text = "This is a terrible product! " * 50000  # ~1.4M chars
        start_time = time.time()
        flag = get_consistency_flag(huge_text, 1)
        duration = time.time() - start_time
        self.assertEqual(flag, "consistent")
        self.assertLess(duration, 3.0, f"Took too long for huge text: {duration}s")

    def test_mocked_polarity_boundary_cases(self):
        from unittest.mock import patch
        
        # We mock get_analyzer to return a mock analyzer with predefined compound scores.
        with patch('backend.signals.consistency.get_analyzer') as mock_get_analyzer:
            mock_analyzer = mock_get_analyzer.return_value
            
            # Sub-test 1: compound is exactly -0.3
            mock_analyzer.polarity_scores.return_value = {"compound": -0.3}
            # rating >= 4, compound <= -0.3 -> contradiction
            self.assertEqual(get_consistency_flag("dummy", 4), "contradiction")
            self.assertEqual(get_consistency_flag("dummy", 5), "contradiction")
            # rating <= 2, compound <= -0.3 -> consistent (not contradiction, and not -0.3 < compound < 0.3)
            self.assertEqual(get_consistency_flag("dummy", 1), "consistent")
            self.assertEqual(get_consistency_flag("dummy", 2), "consistent")
            # rating 3 -> consistent
            self.assertEqual(get_consistency_flag("dummy", 3), "consistent")

            # Sub-test 2: compound is -0.299 (just above -0.3)
            mock_analyzer.polarity_scores.return_value = {"compound": -0.299}
            # -0.3 < compound < 0.3 -> neutral_text regardless of rating
            for r in [1, 2, 3, 4, 5]:
                self.assertEqual(get_consistency_flag("dummy", r), "neutral_text")

            # Sub-test 3: compound is exactly 0.3
            mock_analyzer.polarity_scores.return_value = {"compound": 0.3}
            # rating <= 2, compound >= 0.3 -> contradiction
            self.assertEqual(get_consistency_flag("dummy", 1), "contradiction")
            self.assertEqual(get_consistency_flag("dummy", 2), "contradiction")
            # rating >= 4, compound >= 0.3 -> consistent
            self.assertEqual(get_consistency_flag("dummy", 4), "consistent")
            self.assertEqual(get_consistency_flag("dummy", 5), "consistent")
            # rating 3 -> consistent
            self.assertEqual(get_consistency_flag("dummy", 3), "consistent")

            # Sub-test 4: compound is 0.299 (just below 0.3)
            mock_analyzer.polarity_scores.return_value = {"compound": 0.299}
            # -0.3 < compound < 0.3 -> neutral_text regardless of rating
            for r in [1, 2, 3, 4, 5]:
                self.assertEqual(get_consistency_flag("dummy", r), "neutral_text")

if __name__ == "__main__":
    unittest.main()
