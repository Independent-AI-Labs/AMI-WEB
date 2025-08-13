"""Path validation and manipulation utilities."""

from pathlib import Path
from typing import Any

from loguru import logger


def validate_path(path: str | Path, must_exist: bool = False) -> Path:
    """Validate and normalize file path.

    Prevents path traversal attacks and validates path safety.

    Args:
        path: Path to validate
        must_exist: Whether path must exist

    Returns:
        Validated Path object

    Raises:
        ValueError: If path is invalid or unsafe
        FileNotFoundError: If must_exist=True and path doesn't exist
    """
    if not path:
        raise ValueError("Path cannot be empty")

    # Convert to Path object
    path_obj = Path(path) if not isinstance(path, Path) else path

    # Resolve to absolute path
    try:
        path_obj = path_obj.resolve()
    except (OSError, RuntimeError) as e:
        raise ValueError(f"Invalid path: {e}") from e

    # Check for path traversal attempts
    try:
        # Get the real path (follows symlinks)
        real_path = path_obj.resolve(strict=False)

        # Check if path contains suspicious patterns
        path_str = str(real_path)
        if ".." in path_str or "~" in path_str:
            raise ValueError(f"Path contains suspicious patterns: {path_str}")

    except Exception as e:
        raise ValueError(f"Path validation failed: {e}") from e

    # Check existence if required
    if must_exist and not path_obj.exists():
        raise FileNotFoundError(f"Path does not exist: {path_obj}")

    return path_obj


def ensure_directory(path: str | Path) -> Path:
    """Ensure directory exists, create if necessary.

    Args:
        path: Directory path

    Returns:
        Path object for the directory

    Raises:
        ValueError: If path is invalid
        PermissionError: If cannot create directory
    """
    dir_path = validate_path(path, must_exist=False)

    if dir_path.exists():
        if not dir_path.is_dir():
            raise ValueError(f"Path exists but is not a directory: {dir_path}")
    else:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")
        except (OSError, PermissionError) as e:
            raise PermissionError(f"Cannot create directory {dir_path}: {e}") from e

    return dir_path


def safe_join(*parts: Any) -> Path:
    """Safely join path components.

    Args:
        *parts: Path components to join

    Returns:
        Joined Path object

    Raises:
        ValueError: If resulting path is unsafe
    """
    # Convert all parts to strings
    str_parts = [str(p) for p in parts if p]

    if not str_parts:
        raise ValueError("No path components provided")

    # Join and validate
    joined = Path(*str_parts)
    return validate_path(joined, must_exist=False)


def get_safe_filename(filename: str, max_length: int = 255) -> str:
    """Convert string to safe filename.

    Removes or replaces unsafe characters.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Safe filename string
    """
    if not filename:
        return "unnamed"

    # Remove path separators and null bytes
    unsafe_chars = ["\\", "/", "\0", ":", "*", "?", '"', "<", ">", "|"]
    for char in unsafe_chars:
        filename = filename.replace(char, "_")

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # Limit length
    if len(filename) > max_length:
        # Keep extension if present
        if "." in filename:
            name, ext = filename.rsplit(".", 1)
            max_name_length = max_length - len(ext) - 1
            filename = f"{name[:max_name_length]}.{ext}"
        else:
            filename = filename[:max_length]

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed"

    return filename


def find_project_root(marker_files: list[str] = None) -> Path | None:
    """Find project root directory by looking for marker files.

    Args:
        marker_files: List of files that indicate project root
                     (default: [".git", "pyproject.toml", "setup.py"])

    Returns:
        Project root Path or None if not found
    """
    if marker_files is None:
        marker_files = [".git", "pyproject.toml", "setup.py", "package.json"]

    current = Path.cwd()

    while current != current.parent:
        for marker in marker_files:
            if (current / marker).exists():
                return current
        current = current.parent

    return None
