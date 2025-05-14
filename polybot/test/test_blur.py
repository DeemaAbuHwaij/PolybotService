from polybot.img_proc import Img
import os

def test_blur_filter():
    test_image_path = os.path.join(os.path.dirname(__file__), "photos", "beatles.jpeg")
    img = Img(test_image_path)

    blurred = img.blur()
    assert blurred is not None, "Blurred image is None"
    assert blurred.size == img.original.size, "Blurred image size does not match original"
