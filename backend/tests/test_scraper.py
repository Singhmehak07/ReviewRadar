import unittest
import os
import asyncio
from backend.scraper.flipkart import (
    transform_to_reviews_url,
    scrape_flipkart_reviews
)


class TestScraper(unittest.TestCase):
    def test_transform_to_reviews_url(self):
        # Product detail page URL containing /p/
        prod_url = (
            "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/"
            "itm2d83c0d7630f1?pid=MOBGTAGPAQJ3Z4H5"
        )
        reviews_url = transform_to_reviews_url(prod_url, 2)
        self.assertIn("/product-reviews/", reviews_url)
        self.assertNotIn("/p/", reviews_url)
        self.assertIn("page=2", reviews_url)
        self.assertIn("pid=MOBGTAGPAQJ3Z4H5", reviews_url)

        # Reviews page URL already containing /product-reviews/
        rev_url = (
            "https://www.flipkart.com/apple-iphone-15-black-128-gb/"
            "product-reviews/itm2d83c0d7630f1?pid=MOBGTAGPAQJ3Z4H5&page=1"
        )
        reviews_url_2 = transform_to_reviews_url(rev_url, 3)
        self.assertIn("/product-reviews/", reviews_url_2)
        self.assertIn("page=3", reviews_url_2)

    def test_scrape_mock_file(self):
        # Load local HTML file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        mock_file_path = os.path.join(base_dir, "mock_flipkart.html")
        mock_url = f"file:///{mock_file_path.replace(os.sep, '/')}"

        # Scrape mock page
        reviews = asyncio.run(scrape_flipkart_reviews(mock_url))

        self.assertEqual(len(reviews), 2)

        # Review 1 assertions
        self.assertEqual(reviews[0]["rating"], 5)
        # combined title and text, suffix removed:
        # "Excellent product. I really loved this phone. Best purchase ever!"
        expected_txt_1 = (
            "Excellent product. I really loved this phone. Best purchase ever!"
        )
        self.assertEqual(reviews[0]["text"], expected_txt_1)

        # Review 2 assertions
        self.assertEqual(reviews[1]["rating"], 1)
        expected_txt_2 = "Terrible. The item arrived broken. Returning it."
        self.assertEqual(reviews[1]["text"], expected_txt_2)
