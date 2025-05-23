from pathlib import Path
from matplotlib.image import imread, imsave
import random



def rgb2gray(rgb):
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    gray = 0.2989 * r + 0.5870 * g + 0.1140 * b
    return gray


class Img:

    def __init__(self, path):
        """
        Do not change the constructor implementation
        """
        self.path = Path(path)
        self.data = rgb2gray(imread(path)).tolist()

    def save_img(self):
        """
        Do not change the below implementation
        """
        new_path = self.path.with_name(self.path.stem + '_filtered' + self.path.suffix)
        imsave(new_path, self.data, cmap='gray')
        return new_path

    def blur(self, blur_level=16):

        height = len(self.data)
        width = len(self.data[0])
        filter_sum = blur_level ** 2

        result = []
        for i in range(height - blur_level + 1):
            row_result = []
            for j in range(width - blur_level + 1):
                sub_matrix = [row[j:j + blur_level] for row in self.data[i:i + blur_level]]
                average = sum(sum(sub_row) for sub_row in sub_matrix) // filter_sum
                row_result.append(average)
            result.append(row_result)

        self.data = result

    def contour(self):
        for i, row in enumerate(self.data):
            res = []
            for j in range(1, len(row)):
                res.append(abs(row[j-1] - row[j]))

            self.data[i] = res

    def rotate(self):
        # TODO remove the `raise` below, and write your implementation
        # Get height and width of the original image
        height = len(self.data)
        width = len(self.data[0])

        # Initialize a new list to store the rotated image
        rotated_data = []

        for j in range(width):
            new_row = []
            for i in range(height - 1, -1, -1): # The loop goes from the last row to the first row
                new_row.append(self.data[i][j]) #Builds a vertical slice of the original image, from bottom to top, and stores it as a row in the rotated image.
            rotated_data.append(new_row) # Append the constructed row to the rotated image

        self.data = rotated_data

    def salt_n_pepper(self):
        # TODO remove the `raise` below, and write your implementation
        new_data = []

        # Loop through each row in the image
        for row in self.data:
            new_row = []
            # Loop through each pixel in the current row
            for pixel in row:
                rand_val = random.random()  # Generate Random number between 0 and 1
                if rand_val < 0.2:
                    new_row.append(255)  # Salt (white pixel)
                elif rand_val > 0.8:
                    new_row.append(0)  # Pepper (black pixel)
                else:
                    new_row.append(pixel)  # Keep original
            new_data.append(new_row)

        self.data = new_data

    #Implementation instruction for horizontal concatenation:
    def concat(self, other_img, direction='horizontal'):
        # TODO remove the `raise` below, and write your implementation
        if not isinstance(other_img, Img):
            raise RuntimeError("The provided object is not an instance of Img.")

        if direction == 'horizontal':
            self_height = len(self.data)
            other_height = len(other_img.data)
            if self_height  != other_height:
                raise RuntimeError("Cannot concatenate horizontally: different heights.")

            # Concatenate row by row
            new_data = []
            for self_row, other_row in zip(self.data, other_img.data): #pairs up corresponding rows from both images
                new_data.append(self_row + other_row) #concatenates the two lists

            self.data = new_data

        elif direction == 'vertical':
            self_width = len(self.data[0])
            other_width = len(other_img.data[0])

            if self_width != other_width:
                raise RuntimeError("Cannot concatenate vertically: different widths.")

            self.data = self.data + other_img.data #concatenates the lists

        else:
            raise RuntimeError("Invalid direction.")

    def segment(self):
        # TODO remove the `raise` below, and write your implementation
        new_data = []
        # Loop through each row in the grayscale image
        for row in self.data:
            new_row = []
            # Loop through each pixel in the current row
            for pixel in row:
                if pixel > 100:
                    new_row.append(255)  # White pixel
                else:
                    new_row.append(0)  # Black pixel
            new_data.append(new_row)

        self.data = new_data
