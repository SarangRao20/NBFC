import os
import base64

def encode_image(image_path: str) -> str:
    """Read a local image file and encode it as a base64 string."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
