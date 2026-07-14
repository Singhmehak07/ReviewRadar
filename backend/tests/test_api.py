import unittest
import os
from fastapi.testclient import TestClient
from backend.main import app


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_scrape_endpoint_success(self):
        # Path to local mock HTML file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        mock_file_path = os.path.join(base_dir, "mock_flipkart.html")
        mock_url = f"file:///{mock_file_path.replace(os.sep, '/')}"

        # Call the GET /scrape endpoint
        response = self.client.get(f"/scrape?url={mock_url}")
        self.assertEqual(response.status_code, 200)
        reviews = response.json()
        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0]["rating"], 5)
        expected_txt_1 = (
            "Excellent product. I really loved this phone. Best purchase ever!"
        )
        self.assertEqual(reviews[0]["text"], expected_txt_1)
        self.assertEqual(reviews[1]["rating"], 1)
        expected_txt_2 = "Terrible. The item arrived broken. Returning it."
        self.assertEqual(reviews[1]["text"], expected_txt_2)

    def test_scrape_endpoint_502(self):
        # Pass an empty local file to trigger the 502 error
        base_dir = os.path.dirname(os.path.abspath(__file__))
        empty_file_path = os.path.join(base_dir, "empty.html")

        # Write empty html file
        with open(empty_file_path, "w") as f:
            f.write("<html><body>No reviews here</body></html>")

        try:
            mock_url = f"file:///{empty_file_path.replace(os.sep, '/')}"
            response = self.client.get(f"/scrape?url={mock_url}")
            self.assertEqual(response.status_code, 502)
            self.assertIn("No reviews scraped", response.json()["detail"])
        finally:
            # Clean up the temp empty file
            if os.path.exists(empty_file_path):
                os.remove(empty_file_path)
