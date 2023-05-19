import cv2
import numpy as np


def greyscale_image(image):
    image_grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(image_grayscale, cv2.COLOR_GRAY2BGR)


def decode_image_bytes(image_bytes):
    return cv2.imdecode(np.asarray(bytearray(image_bytes), dtype=np.uint8), 3)
