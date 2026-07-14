import unittest
from backend.signals.consistency import clean_text_for_sentiment, get_consistency_flag

class TestConsistency(unittest.TestCase):
    def test_clean_text_for_sentiment(self):
        # ponytail: verify html/url removal, space collapsing, punctuation/casing preservation
        raw_text = "Hello <p>World</p>! Check out http://example.com/foo   and www.example.com. Great!"
        expected = "Hello World ! Check out and Great!"
        self.assertEqual(clean_text_for_sentiment(raw_text), expected)

        # verify casing/punctuation preserved
        self.assertEqual(clean_text_for_sentiment("This is AWESOME!!!"), "This is AWESOME!!!")

    def test_positive_consistent(self):
        # rating=5, positive sentiment -> consistent
        self.assertEqual(get_consistency_flag("This is absolutely wonderful and great!", 5), "consistent")

    def test_contradictions(self):
        # rating=5, negative sentiment -> contradiction
        self.assertEqual(get_consistency_flag("This is terrible, awful, horrible, and absolute garbage.", 5), "contradiction")
        # rating=1, positive sentiment -> contradiction
        self.assertEqual(get_consistency_flag("This is absolutely wonderful and great!", 1), "contradiction")

    def test_neutral_cases(self):
        # rating=3, neutral sentiment -> neutral_text
        self.assertEqual(get_consistency_flag("This is a book.", 3), "neutral_text")

    def test_empty_or_whitespace(self):
        # rating=4, empty -> no_text
        self.assertEqual(get_consistency_flag("", 4), "no_text")
        self.assertEqual(get_consistency_flag("   ", 4), "no_text")
        self.assertEqual(get_consistency_flag("<p></p>", 4), "no_text")
