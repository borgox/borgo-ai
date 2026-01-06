"""
Image Module - Image viewing and description for borgo-ai
Uses terminal-based image display and optional vision models
"""
import os
import base64
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
import subprocess


@dataclass
class ImageInfo:
    """Information about an image"""
    filepath: str
    filename: str
    width: int
    height: int
    format: str
    size_bytes: int
    success: bool
    error: Optional[str] = None


class ImageViewer:
    """
    Display images in the terminal.
    
    Supports multiple methods:
    1. Kitty graphics protocol (best quality)
    2. iTerm2 inline images
    3. Sixel graphics
    4. ASCII art fallback
    """
    
    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'}
    
    def __init__(self):
        self.display_method = self._detect_display_method()
    
    def _detect_display_method(self) -> str:
        """Detect the best display method for current terminal"""
        term = os.environ.get('TERM', '')
        term_program = os.environ.get('TERM_PROGRAM', '')
        
        # Check for Kitty
        if 'kitty' in term.lower() or os.environ.get('KITTY_WINDOW_ID'):
            return 'kitty'
        
        # Check for iTerm2
        if term_program == 'iTerm.app':
            return 'iterm2'
        
        # Check for Sixel support
        if self._check_sixel_support():
            return 'sixel'
        
        # Fallback to ASCII
        return 'ascii'
    
    def _check_sixel_support(self) -> bool:
        """Check if terminal supports Sixel"""
        # This is a simplified check
        term = os.environ.get('TERM', '')
        return 'sixel' in term.lower() or 'mlterm' in term.lower()
    
    def get_image_info(self, filepath: str) -> ImageInfo:
        """Get information about an image"""
        path = Path(filepath)
        
        if not path.exists():
            return ImageInfo(
                filepath=str(path),
                filename=path.name,
                width=0, height=0,
                format='',
                size_bytes=0,
                success=False,
                error=f"File not found: {filepath}"
            )
        
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            return ImageInfo(
                filepath=str(path),
                filename=path.name,
                width=0, height=0,
                format=path.suffix,
                size_bytes=path.stat().st_size,
                success=False,
                error=f"Unsupported format: {path.suffix}"
            )
        
        try:
            from PIL import Image
            with Image.open(path) as img:
                width, height = img.size
                img_format = img.format
        except ImportError:
            # Fallback without PIL
            width, height = 0, 0
            img_format = path.suffix[1:].upper()
        except Exception as e:
            return ImageInfo(
                filepath=str(path),
                filename=path.name,
                width=0, height=0,
                format=path.suffix,
                size_bytes=path.stat().st_size,
                success=False,
                error=str(e)
            )
        
        return ImageInfo(
            filepath=str(path),
            filename=path.name,
            width=width,
            height=height,
            format=img_format,
            size_bytes=path.stat().st_size,
            success=True
        )
    
    def display(self, filepath: str, max_width: int = 80) -> str:
        """Display an image in the terminal"""
        info = self.get_image_info(filepath)
        
        if not info.success:
            return f"❌ Cannot display image: {info.error}"
        
        # Show info first
        output = f"🖼️  {info.filename} ({info.width}x{info.height}, {info.format})\n"
        
        if self.display_method == 'kitty':
            output += self._display_kitty(filepath)
        elif self.display_method == 'iterm2':
            output += self._display_iterm2(filepath)
        elif self.display_method == 'sixel':
            output += self._display_sixel(filepath, max_width)
        else:
            output += self._display_ascii(filepath, max_width)
        
        return output
    
    def _display_kitty(self, filepath: str) -> str:
        """Display using Kitty graphics protocol"""
        try:
            with open(filepath, 'rb') as f:
                data = base64.b64encode(f.read()).decode('ascii')
            
            # Kitty graphics protocol
            return f"\033_Ga=T,f=100;{data}\033\\"
        except Exception as e:
            return self._display_ascii(filepath, 60)
    
    def _display_iterm2(self, filepath: str) -> str:
        """Display using iTerm2 inline images"""
        try:
            with open(filepath, 'rb') as f:
                data = base64.b64encode(f.read()).decode('ascii')
            
            # iTerm2 inline image protocol
            return f"\033]1337;File=inline=1:{data}\007"
        except Exception as e:
            return self._display_ascii(filepath, 60)
    
    def _display_sixel(self, filepath: str, max_width: int) -> str:
        """Display using Sixel graphics"""
        try:
            result = subprocess.run(
                ['img2sixel', '-w', str(max_width * 10), filepath],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return self._display_ascii(filepath, max_width)
    
    def _display_ascii(self, filepath: str, max_width: int = 60) -> str:
        """Display image as ASCII art"""
        try:
            from PIL import Image
            
            # ASCII characters from dark to light
            ASCII_CHARS = " .:-=+*#%@"
            
            img = Image.open(filepath)
            
            # Convert to grayscale
            img = img.convert('L')
            
            # Calculate new dimensions
            aspect_ratio = img.height / img.width
            new_width = min(max_width, img.width)
            new_height = int(new_width * aspect_ratio * 0.5)  # *0.5 because chars are taller than wide
            
            # Resize
            img = img.resize((new_width, new_height))
            
            # Convert to ASCII
            pixels = list(img.getdata())
            ascii_str = ""
            
            for i, pixel in enumerate(pixels):
                ascii_str += ASCII_CHARS[pixel * len(ASCII_CHARS) // 256]
                if (i + 1) % new_width == 0:
                    ascii_str += '\n'
            
            return ascii_str
        
        except ImportError:
            return "[Install PIL for ASCII preview: pip install Pillow]"
        except Exception as e:
            return f"[Cannot generate ASCII art: {e}]"
    
    def to_base64(self, filepath: str) -> Optional[str]:
        """Convert image to base64 for API usage"""
        try:
            with open(filepath, 'rb') as f:
                return base64.b64encode(f.read()).decode('ascii')
        except:
            return None


class ImageDescriber:
    """
    Describe images using vision-capable models.
    
    Note: llama3.1:8b doesn't support vision.
    This is prepared for when you upgrade to a vision model like:
    - llava (local)
    - llama3.2-vision (when available)
    """
    
    def __init__(self, model: str = "llava"):
        self.model = model
        self.viewer = ImageViewer()
    
    def describe(self, filepath: str) -> str:
        """Describe an image using a vision model"""
        info = self.viewer.get_image_info(filepath)
        
        if not info.success:
            return f"Cannot process image: {info.error}"
        
        # Check if we have a vision-capable model
        try:
            import requests
            
            # Get base64 image
            base64_image = self.viewer.to_base64(filepath)
            if not base64_image:
                return "Failed to read image"
            
            # Try Ollama vision API
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": "Describe this image in detail. What do you see?",
                    "images": [base64_image],
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json().get("response", "No description generated")
            else:
                return f"Vision model not available. Install with: ollama pull {self.model}"
        
        except requests.exceptions.ConnectionError:
            return "Ollama not running. Start with: ollama serve"
        except Exception as e:
            return f"Image description failed: {e}"


# Convenience functions
_viewer: Optional[ImageViewer] = None

def get_viewer() -> ImageViewer:
    """Get or create image viewer"""
    global _viewer
    if _viewer is None:
        _viewer = ImageViewer()
    return _viewer


def view_image(filepath: str, max_width: int = 80) -> str:
    """View an image in the terminal"""
    return get_viewer().display(filepath, max_width)


def get_image_info(filepath: str) -> ImageInfo:
    """Get information about an image"""
    return get_viewer().get_image_info(filepath)


def describe_image(filepath: str, model: str = "llava") -> str:
    """Describe an image using a vision model"""
    describer = ImageDescriber(model)
    return describer.describe(filepath)
