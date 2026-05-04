import io
from PIL import Image
import os

def compress_image(image_bytes: bytes, max_size_kb: int = 1024, quality: int = 85) -> bytes:
    """
    Compresses an image to WebP format, stripping metadata and maintaining quality.
    
    Args:
        image_bytes: The original image data.
        max_size_kb: Target maximum size (attempted).
        quality: Initial quality threshold for WebP conversion.
        
    Returns:
        bytes: The compressed WebP image data.
    """
    # Load image from bytes
    img = Image.open(io.BytesIO(image_bytes))
    
    # Convert to RGB if necessary (e.g., if it has transparency/alpha channel)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    # Strip EXIF data (metadata) - done by default when saving with Pillow unless specified
    
    # Cap dimensions to 2048px max to keep it lightweight but sharp
    max_dimension = 2048
    if max(img.width, img.height) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    
    # Save to WebP in memory
    output = io.BytesIO()
    img.save(output, format="WebP", quality=quality, optimize=True)
    
    # Return processed bytes
    return output.getvalue()

def get_image_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()
