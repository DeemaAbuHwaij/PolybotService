import unittest
from unittest.mock import patch, mock_open
from polybot.img_proc import Img

class TestImgDetect(unittest.TestCase):

    def setUp(self):
        self.img = Img("polybot/test/beatles.jpeg")

    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_data")
    @patch("requests.post")
    def test_detect_returns_expected_labels(self, mock_post, mock_file):
        # Simulate YOLO API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"labels": ["person", "car"]}

        labels = self.img.detect()
        self.assertIsInstance(labels, list)
        self.assertIn("person", labels)
        self.assertIn("car", labels)

    @patch("builtins.open", new_callable=mock_open, read_data=b"fake_image_data")
    @patch("requests.post")
    def test_detect_empty_response(self, mock_post, mock_file):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"labels": []}

        labels = self.img.detect()
        self.assertEqual(labels, [])

if __name__ == '__main__':
    unittest.main()
