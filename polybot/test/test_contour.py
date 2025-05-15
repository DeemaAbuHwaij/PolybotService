import unittest
from polybot.img_proc import Img
import os

img_path = 'polybot/test/beatles.jpeg' if '/polybot/test' not in os.getcwd() else 'beatles.jpeg'


class TestImgContour(unittest.TestCase):

    def setUp(self):
        self.img = Img(img_path)
        self.original_shape = (len(self.img.data), len(self.img.data[0]))

    def test_contour_preserves_dimensions(self):
        self.img.contour()
        new_shape = (len(self.img.data), len(self.img.data[0]))
        self.assertEqual(self.original_shape, new_shape)

    def test_contour_changes_pixel_values(self):
        original_data = [row[:] for row in self.img.data]
        self.img.contour()
        self.assertNotEqual(original_data, self.img.data)


if __name__ == '__main__':
    unittest.main()
