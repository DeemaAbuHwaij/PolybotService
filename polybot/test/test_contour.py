from polybot.img_proc import Img
import os

def test_contour_filter():
    test_image_path = os.path.join(os.path.dirname(__file__), "photos", "beatles.jpeg")
    img = Img(test_image_path)

    contoured = img.contour()
    assert contoured is not None, "Contour image is None"
    assert contoured.size == img.original.size, "Contour image size does not match original"
