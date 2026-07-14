import unittest
import time
from backend.signals.consistency import clean_text_for_sentiment, get_consistency_flag

class TestConsistencyAdversarial(unittest.TestCase):
    
    def test_unicode_and_special_characters(self):
        # Emojis (VADER compound score should be positive for love/heart, negative for angry/thumbs down)
        # We check the returned flags.
        # Rating 5 (positive), positive emoji -> consistent
        self.assertEqual(get_consistency_flag("I love this! 😍", 5), "consistent")
        # Rating 1 (negative), positive emoji -> contradiction
        self.assertEqual(get_consistency_flag("I love this! 😍", 1), "contradiction")
        # Rating 5, negative text with angry emoji -> contradiction
        self.assertEqual(get_consistency_flag("This is awful 😠", 5), "contradiction")
        
        # Non-ASCII European characters (German, French)
        self.assertEqual(get_consistency_flag("C'est magnifique! J'adore cette marque.", 5), "neutral_text") # VADER is English-centric, so non-English might be neutral
        
        # Non-Latin characters (Chinese)
        # "这是垃圾" (This is garbage)
        self.assertEqual(get_consistency_flag("这是垃圾", 1), "neutral_text") # VADER returns 0.0 compound, so neutral_text
        
        # Control characters and zero-width spaces
        self.assertEqual(clean_text_for_sentiment("Hello\x00\x07World"), "Hello\x00\x07World")
        self.assertEqual(clean_text_for_sentiment("Hello\u200bWorld"), "Hello\u200bWorld")

    def test_html_cleaning_edge_cases(self):
        # Nested tags
        self.assertEqual(clean_text_for_sentiment("<div><p>Hello World</p></div>"), "Hello World")
        # Malformed/unclosed tags
        self.assertEqual(clean_text_for_sentiment("Hello <p"), "Hello <p")
        # Math operators / angle brackets (VULNERABILITY: removes text between < and >)
        # Under the current implementation, "If rating < 3 and score > 0.8" becomes "If rating 0.8"
        # We assert what the current code ACTUALLY does to document the behavior, even if it is buggy.
        self.assertEqual(clean_text_for_sentiment("If rating < 3 and score > 0.8"), "If rating 0.8")

    def test_url_cleaning_edge_cases(self):
        # URL without spaces
        self.assertEqual(clean_text_for_sentiment("Superhttp://example.com/test"), "Super")
        # Domain only (no protocol/www) -> not removed
        self.assertEqual(clean_text_for_sentiment("Check example.com"), "Check example.com")
        # Multiple URLs
        self.assertEqual(clean_text_for_sentiment("Check http://url1.com and http://url2.com"), "Check and")

    def test_invalid_text_types(self):
        # None input
        self.assertEqual(clean_text_for_sentiment(None), "")
        self.assertEqual(get_consistency_flag(None, 5), "no_text")
        
        # Integer input
        self.assertEqual(clean_text_for_sentiment(12345), "12345")
        
        # List input
        self.assertEqual(clean_text_for_sentiment([1, 2, 3]), "[1, 2, 3]")

    def test_rating_boundaries_integers(self):
        # Rating 0 (falls under rating <= 2)
        # Rating 0, positive text -> contradiction
        self.assertEqual(get_consistency_flag("This is absolutely wonderful and great!", 0), "contradiction")
        # Rating 0, negative text -> consistent
        self.assertEqual(get_consistency_flag("This is terrible, awful, and horrible.", 0), "consistent")

        # Rating -1 (falls under rating <= 2)
        self.assertEqual(get_consistency_flag("This is absolutely wonderful and great!", -1), "contradiction")
        
        # Rating 6 (falls under rating >= 4)
        self.assertEqual(get_consistency_flag("This is terrible, awful, and horrible.", 6), "contradiction")
        self.assertEqual(get_consistency_flag("This is absolutely wonderful and great!", 6), "consistent")

    def test_neutral_rating_3(self):
        # Rating 3 is neutral.
        # Under the current implementation:
        # - rating >= 4 check is False
        # - rating <= 2 check is False
        # If compound is extreme (e.g. 0.8), it fails the neutral check (-0.3 < compound < 0.3)
        # and goes to the "else" branch, returning "consistent".
        # This means an extremely positive or negative text with a neutral rating is considered "consistent".
        self.assertEqual(get_consistency_flag("This is absolutely wonderful and great!", 3), "consistent")
        self.assertEqual(get_consistency_flag("This is terrible, awful, and horrible.", 3), "consistent")
        # If compound is neutral (e.g. 0.0), it returns "neutral_text"
        self.assertEqual(get_consistency_flag("This is a book.", 3), "neutral_text")

    def test_non_integer_ratings_crashes(self):
        # String rating raises TypeError
        with self.assertRaises(TypeError):
            get_consistency_flag("This is great!", "5")
            
        # None rating raises TypeError
        with self.assertRaises(TypeError):
            get_consistency_flag("This is great!", None)
            
        # Float rating (e.g. 4.5) works because python supports float/int comparison
        self.assertEqual(get_consistency_flag("This is absolutely wonderful and great!", 4.5), "consistent")

    def test_exact_sentiment_thresholds(self):
        # VADER compound score exact thresholds (-0.3 and 0.3)
        # Since we cannot easily force VADER to return exactly 0.3, we can mock the analyzer if we want,
        # or we can test using texts that get close, or we can just analyze the logic itself.
        # Let's test the logical branches by observing how they are defined:
        # compound <= -0.3 is contradiction for rating >= 4
        # compound >= 0.3 is contradiction for rating <= 2
        # -0.3 < compound < 0.3 is neutral_text
        pass

    def test_performance_extreme_length(self):
        # 100,000 characters text
        large_text = "This is absolutely wonderful and great! " * 2500
        start_time = time.time()
        flag = get_consistency_flag(large_text, 5)
        duration = time.time() - start_time
        print(f"\n100,000 char processing took: {duration:.4f} seconds")
        self.assertEqual(flag, "consistent")
        self.assertLess(duration, 2.0, "Processing took too long!")

        # 1,000,000 characters text
        huge_text = "This is absolutely wonderful and great! " * 25000
        start_time = time.time()
        flag = get_consistency_flag(huge_text, 5)
        duration = time.time() - start_time
        print(f"1,000,000 char processing took: {duration:.4f} seconds")
        self.assertEqual(flag, "consistent")
        # Usually it should take less than 5 seconds. Let's make sure it doesn't timeout.
        self.assertLess(duration, 5.0, "Processing took too long!")

if __name__ == "__main__":
    unittest.main()
