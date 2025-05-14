import unittest
from polybot.img_proc import Img
import os

img_path = 'polybot/test/beatles.jpeg' if '/polybot/test' not in os.getcwd() else 'beatles.jpeg'


class TestImgDetect(unittest.TestCase):

    def setUp(self):
        self.img = Img(img_path)

    def test_detect_returns_labels(self):
        labels = self.img.detect()
        self.assertIsInstance(labels, list)
        # If expected labels are known, you can check:
        # self.assertIn("person", labels)

    def test_detect_is_not_empty(self):
        labels = self.img.detect()
        self.assertTrue(len(labels) > 0, "No objects detected")


if __name__ == '__main__':
    unittest.main()
