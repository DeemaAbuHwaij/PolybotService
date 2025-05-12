import os
import requests
from polybot.img_proc import Img

def test_detect_filter():
    # Arrange
    test_image_path = os.path.join(os.path.dirname(__file__), "photos", "beatles.jpeg")
    img = Img(test_image_path)

    # Act
    output_path = img.save_img()

    try:
        response = requests.post("http://10.0.1.66:8080/predict", files={"file": open(output_path, "rb")})
        response.raise_for_status()
    except Exception as e:
        assert False, f"Request to YOLO failed: {e}"

    # Assert
    data = response.json()
    assert "labels" in data, "Response does not contain 'labels'"
    assert isinstance(data["labels"], list), "Labels is not a list"

