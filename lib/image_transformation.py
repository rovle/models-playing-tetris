"""
Example usage

Load an image:
image = load_image("screens/screenshot_1.png")

Apply random transformations:
image = apply_noise(image, "gaussian", 1)
image = apply_color_transformations(image, 1.8, 0.8, 1.5, 30)
image = apply_resize(image, 500, 500)
image = apply_rotation(image, 10)

Display the augmented image (press Esc to exit):
show_image(image)
"""

import cv2
from PIL import Image
import numpy as np
import random
import base64

def load_image(file_path):
    """
    Load an image from a file.
    Args:
        file_path (str): Path to the image file.
    Returns:
        np.ndarray: The loaded image.
    """
    return cv2.imread(file_path)


def apply_noise(image, noise_type="gaussian", noise_factor=1):
    """
    Apply random noise to an image.
    Args:
        image (np.ndarray): The input image.
        noise_type (string): The type of noise to apply: gaussian or salt_and_pepper.
        noise_factor (float): The factor controlling the amount of noise to apply.
    Returns:
        np.ndarray: The augmented image with random noise.
    """
    if noise_type == "gaussian":
        noise = np.random.normal(0, noise_factor, image.shape).astype(np.uint8)
        noisy_image = cv2.add(image, noise)
    elif noise_type == "salt_and_pepper":
        prob = 0.05
        noisy_image = image.copy()
        for i in range(image.shape[0]):
            for j in range(image.shape[1]):
                if random.random() < prob / 2:
                    noisy_image[i][j] = 0
                elif random.random() < prob:
                    noisy_image[i][j] = 255
    else:
        raise ValueError(
            "Invalid noise type. Supported types are 'gaussian' and 'salt_and_pepper'."
        )
    return noisy_image


def apply_color_transformations(
    image, brightness_factor, contrast_factor, saturation_factor, hue_factor
):
    """
    Apply random color transformations to an image.
    Args:
        image (np.ndarray): The input image.
        brightness_factor (float): The factor controlling the brightness transformation.
        contrast_factor (float): The factor controlling the contrast transformation.
        saturation_factor (float): The factor controlling the saturation transformation.
        hue_factor (float): The factor controlling the hue transformation.
    Returns:
        np.ndarray: The augmented image with random color transformations.
    """
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv_image = hsv_image.astype(np.float32)
    hsv_image[..., 1] *= saturation_factor
    hsv_image[..., 2] *= brightness_factor
    hsv_image[..., 0] = (hsv_image[..., 0] + hue_factor) % 180
    hsv_image = np.clip(hsv_image, 0, 255)
    augmented_image = cv2.cvtColor(hsv_image.astype(np.uint8), cv2.COLOR_HSV2BGR)
    augmented_image = cv2.convertScaleAbs(
        augmented_image, alpha=contrast_factor, beta=0
    )
    return augmented_image


def apply_resize(image, width=None, height=None):
    """
    Resize an image to a new size.
    Args:
        image (np.ndarray): The input image.
        width (float): The new width of the image.
        height (float): The new height of the image.
    Returns:
        np.ndarray: The resized image.
    """
    if width is None and height is None:
        raise ValueError("At least one of width and height must be provided.")
    if width is None:
        aspect_ratio = height / image.shape[0]
        width = int(image.shape[1] * aspect_ratio)
    elif height is None:
        aspect_ratio = width / image.shape[1]
        height = int(image.shape[0] * aspect_ratio)
    resized_image = cv2.resize(image, (width, height))
    return resized_image


def apply_rotation(image, angle):
    """
    Rotate an image by a given angle.
    Args:
        image (np.ndarray): The input image.
        angle (float): The rotation angle in degrees.
    Returns:
        np.ndarray: The rotated image.
    """
    height, width = image.shape[:2]
    rotation_matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
    rotated_image = cv2.warpAffine(image, rotation_matrix, (width, height))
    return rotated_image


def apply_augmentations(image_path, augmentation_data):
    image = load_image(image_path)

    augmented_images = []
    for aug_name, aug_params in augmentation_data.items():
        if aug_name == "noise":
            augmented_image = apply_noise(image, **aug_params)
        elif aug_name == "color":
            augmented_image = apply_color_transformations(image, **aug_params)
        elif aug_name == "resize":
            augmented_image = apply_resize(image, **aug_params)
        elif aug_name == "rotation":
            augmented_image = apply_rotation(image, **aug_params)
        else:
            continue
        pil_image = Image.fromarray(cv2.cvtColor(augmented_image, cv2.COLOR_BGR2RGB))
        augmented_images.append(pil_image)

        # Show the augmented images (press Esc to close the windows)
        # show_image(augmented_image)
    return augmented_images

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def show_image(image):
    """
    Displays the given image in a new window.
    Press Esc to close the window.

    Args:
        image: The image to be displayed.

    Returns:
        None
    """
    cv2.imshow("Image", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
