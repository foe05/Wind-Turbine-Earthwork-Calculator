"""
Security utilities for safe file operations

⚠️  SECURITY WARNING ⚠️
This module provides critical security functions to prevent path traversal attacks.
Always use validate_safe_path() before accessing user-provided file paths.
"""
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)


def validate_safe_path(filename: str, base_directory: Path) -> Path:
    """
    Validate that a filename is safe and within the allowed directory.

    This function prevents path traversal attacks by:
    1. Rejecting filenames with dangerous path traversal sequences
    2. Canonicalizing the path to resolve any symbolic links or relative components
    3. Verifying the resolved path is within the allowed base directory

    ⚠️  SECURITY CRITICAL: This function must be used for all user-provided filenames
    before any file system operations. Failure to do so may allow attackers to
    read arbitrary files from the server.

    Args:
        filename: User-provided filename to validate (should be basename only)
        base_directory: The allowed directory where files should reside

    Returns:
        Path: Validated and resolved Path object within base_directory

    Raises:
        ValueError: If the filename contains path traversal attempts or
                   resolves to a location outside base_directory

    Examples:
        >>> validate_safe_path("report.pdf", Path("/app/reports"))
        Path('/app/reports/report.pdf')

        >>> validate_safe_path("../../../etc/passwd", Path("/app/reports"))
        ValueError: Path traversal detected

    Security Test Cases:
        - '../../../etc/passwd' -> Rejected (path traversal)
        - '../../.env' -> Rejected (path traversal)
        - '/etc/passwd' -> Rejected (absolute path)
        - '..\\..\\windows\\system32' -> Rejected (Windows traversal)
        - 'subdir/../file.txt' -> Rejected (contains ..)
        - 'report.pdf' -> Accepted (safe filename)
    """
    # Normalize filename to prevent case sensitivity issues
    filename = filename.strip()

    # Reject empty filenames
    if not filename:
        logger.warning("Security: Rejected empty filename")
        raise ValueError("Filename cannot be empty")

    # Check for dangerous path traversal sequences
    dangerous_patterns = [
        '..',      # Parent directory reference
        '/',       # Absolute path or path separator
        '\\',      # Windows path separator
        '\x00',    # Null byte injection
        '%2e',     # URL encoded dot
        '%2f',     # URL encoded forward slash
        '%5c',     # URL encoded backslash
    ]

    # Convert to lowercase for case-insensitive checks
    filename_lower = filename.lower()

    for pattern in dangerous_patterns:
        if pattern in filename_lower:
            logger.warning(
                f"Security: Path traversal attempt detected - "
                f"filename contains '{pattern}': {filename}"
            )
            raise ValueError(
                f"Invalid filename: contains forbidden sequence '{pattern}'"
            )

    # Ensure base_directory is resolved and absolute
    base_directory = base_directory.resolve()

    # Build the full path
    full_path = base_directory / filename

    # Resolve to canonical path (eliminates symlinks and relative components)
    try:
        resolved_path = full_path.resolve()
    except (OSError, RuntimeError) as e:
        logger.error(f"Security: Failed to resolve path '{filename}': {e}")
        raise ValueError(f"Invalid filename: cannot resolve path")

    # Critical security check: Verify resolved path is within base_directory
    try:
        resolved_path.relative_to(base_directory)
    except ValueError:
        logger.warning(
            f"Security: Path traversal detected - "
            f"resolved path '{resolved_path}' is outside base directory '{base_directory}'"
        )
        raise ValueError(
            "Invalid filename: path traversal detected"
        )

    # Additional check: ensure the path doesn't contain any parent references
    # even after resolution (defense in depth)
    path_parts = resolved_path.parts
    if '..' in path_parts or '.' in path_parts[len(base_directory.parts):]:
        logger.warning(
            f"Security: Suspicious path components in '{filename}'"
        )
        raise ValueError(
            "Invalid filename: contains suspicious path components"
        )

    logger.info(f"Security: Validated safe path for filename '{filename}'")
    return resolved_path
