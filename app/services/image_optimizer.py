"""
Image Optimization Service
Resize and strip metadata from images without quality loss
"""

from io import BytesIO
from PIL import Image
from typing import Tuple


class ImageOptimizer:
    """Lossless image optimization: resize + strip metadata"""
    
    MAX_DIMENSION = 2048  # Max width or height
    
    @staticmethod
    def optimize(image_bytes: bytes, content_type: str = "image/png") -> Tuple[bytes, str]:
        """
        Optimize image by resizing (if needed) and stripping metadata.
        Keeps PNG format for transparency support.
        
        Args:
            image_bytes: Original image bytes
            content_type: Original content type
            
        Returns:
            Tuple of (optimized_bytes, content_type)
        """
        try:
            img = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB if RGBA and no transparency, otherwise keep RGBA
            has_transparency = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
            
            # Resize if larger than max dimension (maintain aspect ratio)
            width, height = img.size
            if width > ImageOptimizer.MAX_DIMENSION or height > ImageOptimizer.MAX_DIMENSION:
                if width > height:
                    new_width = ImageOptimizer.MAX_DIMENSION
                    new_height = int(height * (ImageOptimizer.MAX_DIMENSION / width))
                else:
                    new_height = ImageOptimizer.MAX_DIMENSION
                    new_width = int(width * (ImageOptimizer.MAX_DIMENSION / height))
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save optimized image (strip metadata by not copying EXIF)
            output = BytesIO()
            
            if has_transparency:
                # Keep PNG for transparency
                img.save(output, format='PNG', optimize=True)
                return output.getvalue(), "image/png"
            else:
                # Convert to RGB and save as optimized PNG
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(output, format='PNG', optimize=True)
                return output.getvalue(), "image/png"
                
        except Exception:
            # If optimization fails, return original
            return image_bytes, content_type
    
    @staticmethod
    def get_size_reduction(original_size: int, optimized_size: int) -> str:
        """Get human-readable size reduction"""
        if original_size == 0:
            return "0%"
        reduction = ((original_size - optimized_size) / original_size) * 100
        if reduction > 0:
            return f"-{reduction:.1f}%"
        elif reduction < 0:
            return f"+{abs(reduction):.1f}%"
        return "0%"


# Singleton
image_optimizer = ImageOptimizer()
