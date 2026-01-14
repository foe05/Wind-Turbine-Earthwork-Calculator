"""
Branding functions for PDF reports.

Handles company logo validation, processing, and custom footer text
for branded PDF reports.

Author: Wind Energy Site Planning
Version: 2.0 - Enhanced PDF Report Generation
"""

import io
import base64
from typing import Optional, Tuple, Dict, Any

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# Configuration constants
MAX_LOGO_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_LOGO_WIDTH = 2000  # pixels
MAX_LOGO_HEIGHT = 2000  # pixels
SUPPORTED_FORMATS = ['PNG', 'JPEG', 'JPG', 'GIF', 'WEBP']
MAX_FOOTER_LENGTH = 500  # characters


class BrandingError(Exception):
    """Base exception for branding-related errors"""
    pass


class LogoValidationError(BrandingError):
    """Exception raised when logo validation fails"""
    pass


class FooterValidationError(BrandingError):
    """Exception raised when footer validation fails"""
    pass


def validate_logo(
    logo_data: bytes,
    max_size_bytes: int = MAX_LOGO_SIZE_BYTES,
    max_width: int = MAX_LOGO_WIDTH,
    max_height: int = MAX_LOGO_HEIGHT
) -> Dict[str, Any]:
    """
    Validate logo image data for format, size, and dimensions.

    Args:
        logo_data: Raw image bytes
        max_size_bytes: Maximum file size in bytes
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels

    Returns:
        Dictionary with validation results:
        - valid: bool - Whether the logo is valid
        - format: str - Image format (PNG, JPEG, etc.)
        - width: int - Image width in pixels
        - height: int - Image height in pixels
        - size_bytes: int - File size in bytes
        - error: Optional[str] - Error message if invalid

    Raises:
        LogoValidationError: If logo validation fails
    """
    result = {
        'valid': False,
        'format': None,
        'width': None,
        'height': None,
        'size_bytes': len(logo_data),
        'error': None
    }

    # Check file size
    if len(logo_data) > max_size_bytes:
        result['error'] = f"Logo file size ({len(logo_data)} bytes) exceeds maximum ({max_size_bytes} bytes)"
        raise LogoValidationError(result['error'])

    if len(logo_data) == 0:
        result['error'] = "Logo data is empty"
        raise LogoValidationError(result['error'])

    # Validate using PIL if available
    if PIL_AVAILABLE:
        try:
            image = Image.open(io.BytesIO(logo_data))
            result['format'] = image.format
            result['width'] = image.width
            result['height'] = image.height

            # Check format
            if result['format'] not in SUPPORTED_FORMATS:
                result['error'] = f"Unsupported image format: {result['format']}. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
                raise LogoValidationError(result['error'])

            # Check dimensions
            if result['width'] > max_width or result['height'] > max_height:
                result['error'] = f"Logo dimensions ({result['width']}x{result['height']}) exceed maximum ({max_width}x{max_height})"
                raise LogoValidationError(result['error'])

            result['valid'] = True
            return result

        except LogoValidationError:
            raise
        except Exception as e:
            result['error'] = f"Failed to validate logo image: {str(e)}"
            raise LogoValidationError(result['error'])
    else:
        # Basic validation without PIL - just check if it looks like an image
        # Check for common image file signatures
        if logo_data[:8] == b'\x89PNG\r\n\x1a\n':
            result['format'] = 'PNG'
            result['valid'] = True
        elif logo_data[:2] == b'\xff\xd8':
            result['format'] = 'JPEG'
            result['valid'] = True
        elif logo_data[:6] in [b'GIF87a', b'GIF89a']:
            result['format'] = 'GIF'
            result['valid'] = True
        elif logo_data[:4] == b'RIFF' and logo_data[8:12] == b'WEBP':
            result['format'] = 'WEBP'
            result['valid'] = True
        else:
            result['error'] = "Unrecognized image format"
            raise LogoValidationError(result['error'])

        # Note: Without PIL, we can't validate dimensions
        result['width'] = None
        result['height'] = None

        return result


def process_logo(
    logo_data: bytes,
    validate: bool = True,
    max_size_bytes: int = MAX_LOGO_SIZE_BYTES
) -> str:
    """
    Process logo image data and convert to base64 for embedding in reports.

    Args:
        logo_data: Raw image bytes
        validate: Whether to validate the logo before processing
        max_size_bytes: Maximum file size in bytes

    Returns:
        Base64 encoded image string

    Raises:
        LogoValidationError: If validation is enabled and fails
    """
    if validate:
        validation_result = validate_logo(logo_data, max_size_bytes=max_size_bytes)
        if not validation_result['valid']:
            raise LogoValidationError(validation_result.get('error', 'Logo validation failed'))

    # Convert to base64
    logo_base64 = base64.b64encode(logo_data).decode('utf-8')
    return logo_base64


def process_logo_from_file(
    file_path: str,
    validate: bool = True,
    max_size_bytes: int = MAX_LOGO_SIZE_BYTES
) -> str:
    """
    Load logo from file, validate, and convert to base64.

    Args:
        file_path: Path to logo image file
        validate: Whether to validate the logo before processing
        max_size_bytes: Maximum file size in bytes

    Returns:
        Base64 encoded image string

    Raises:
        FileNotFoundError: If file doesn't exist
        LogoValidationError: If validation is enabled and fails
    """
    try:
        with open(file_path, 'rb') as f:
            logo_data = f.read()
        return process_logo(logo_data, validate=validate, max_size_bytes=max_size_bytes)
    except FileNotFoundError:
        raise
    except LogoValidationError:
        raise
    except Exception as e:
        raise BrandingError(f"Failed to process logo from file: {str(e)}")


def validate_footer_text(
    footer_text: str,
    max_length: int = MAX_FOOTER_LENGTH
) -> Dict[str, Any]:
    """
    Validate custom footer text.

    Args:
        footer_text: Footer text to validate
        max_length: Maximum allowed length in characters

    Returns:
        Dictionary with validation results:
        - valid: bool - Whether the footer text is valid
        - length: int - Text length in characters
        - error: Optional[str] - Error message if invalid

    Raises:
        FooterValidationError: If validation fails
    """
    result = {
        'valid': False,
        'length': len(footer_text),
        'error': None
    }

    if len(footer_text) == 0:
        result['error'] = "Footer text cannot be empty"
        raise FooterValidationError(result['error'])

    if len(footer_text) > max_length:
        result['error'] = f"Footer text length ({len(footer_text)}) exceeds maximum ({max_length})"
        raise FooterValidationError(result['error'])

    # Check for potentially problematic characters
    if '\x00' in footer_text:
        result['error'] = "Footer text contains null characters"
        raise FooterValidationError(result['error'])

    result['valid'] = True
    return result


def process_footer_text(
    footer_text: str,
    validate: bool = True,
    max_length: int = MAX_FOOTER_LENGTH
) -> str:
    """
    Process and sanitize footer text for reports.

    Args:
        footer_text: Footer text to process
        validate: Whether to validate the text before processing
        max_length: Maximum allowed length in characters

    Returns:
        Sanitized footer text

    Raises:
        FooterValidationError: If validation is enabled and fails
    """
    if validate:
        validation_result = validate_footer_text(footer_text, max_length=max_length)
        if not validation_result['valid']:
            raise FooterValidationError(validation_result.get('error', 'Footer validation failed'))

    # Sanitize: strip leading/trailing whitespace and normalize newlines
    sanitized = footer_text.strip()
    sanitized = sanitized.replace('\r\n', '\n').replace('\r', '\n')

    return sanitized


def get_logo_data_uri(
    logo_base64: str,
    image_format: Optional[str] = None
) -> str:
    """
    Convert base64 logo data to data URI for HTML embedding.

    Args:
        logo_base64: Base64 encoded image string
        image_format: Image format (png, jpeg, etc.). If None, assumes PNG

    Returns:
        Data URI string (e.g., "data:image/png;base64,...")
    """
    if image_format is None:
        image_format = 'png'

    # Normalize format
    format_lower = image_format.lower()
    if format_lower == 'jpg':
        format_lower = 'jpeg'

    mime_type = f'image/{format_lower}'
    return f'data:{mime_type};base64,{logo_base64}'


def is_pil_available() -> bool:
    """
    Check if PIL (Pillow) is available for image processing.

    Returns:
        True if PIL can be imported, False otherwise
    """
    return PIL_AVAILABLE
