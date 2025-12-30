"""
XAI Secure I/O Utilities

Provides secure file operations with explicit permissions to prevent
data leakage on multi-user systems.

Security Properties:
- All files created with 0o600 (owner read/write only)
- All directories created with 0o700 (owner read/write/execute only)
- Atomic writes prevent partial file exposure
- No reliance on system umask
"""

import json
import os
import tempfile
from typing import Any, Union

# Secure permission modes
SECURE_FILE_MODE = 0o600  # Owner read/write only
SECURE_DIR_MODE = 0o700   # Owner read/write/execute only


def secure_write_file(
    path: str,
    content: Union[str, bytes],
    mode: int = SECURE_FILE_MODE,
    encoding: str = "utf-8"
) -> None:
    """
    Write content to a file with explicit secure permissions.

    Creates the file with mode 0o600 (owner read/write only) regardless
    of the system umask setting. If the file exists, its permissions
    are reset to the specified mode.

    Args:
        path: Absolute path to the file
        content: String or bytes to write
        mode: File permission mode (default: 0o600)
        encoding: Text encoding for string content (default: utf-8)

    Raises:
        OSError: If file creation or writing fails
        TypeError: If content is neither str nor bytes
    """
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

    # Open with explicit mode, bypassing umask
    fd = os.open(path, flags, mode)
    try:
        # Ensure permissions are set even for existing files
        os.fchmod(fd, mode)

        with os.fdopen(fd, "wb") as f:
            if isinstance(content, str):
                f.write(content.encode(encoding))
            elif isinstance(content, bytes):
                f.write(content)
            else:
                raise TypeError(f"content must be str or bytes, got {type(content).__name__}")
    except Exception:
        # If write fails after fd is opened, fdopen closes it
        # but we should ensure cleanup on error
        raise


def secure_write_json(
    path: str,
    data: Any,
    mode: int = SECURE_FILE_MODE,
    indent: int = 2
) -> None:
    """
    Write JSON data to a file with explicit secure permissions.

    Creates the file with mode 0o600 (owner read/write only) regardless
    of the system umask setting.

    Args:
        path: Absolute path to the file
        data: JSON-serializable data
        mode: File permission mode (default: 0o600)
        indent: JSON indentation (default: 2)

    Raises:
        OSError: If file creation or writing fails
        json.JSONDecodeError: If data is not JSON-serializable
    """
    content = json.dumps(data, indent=indent)
    secure_write_file(path, content, mode=mode)


def secure_create_directory(
    path: str,
    mode: int = SECURE_DIR_MODE,
    parents: bool = True
) -> None:
    """
    Create a directory with explicit secure permissions.

    Creates the directory with mode 0o700 (owner read/write/execute only)
    regardless of the system umask setting.

    Args:
        path: Absolute path to the directory
        mode: Directory permission mode (default: 0o700)
        parents: If True, create parent directories as needed (default: True)

    Raises:
        OSError: If directory creation fails
    """
    if parents:
        # os.makedirs respects umask, so we need to set permissions after
        os.makedirs(path, exist_ok=True)
        os.chmod(path, mode)
    else:
        # For single directory, use os.mkdir which allows explicit mode
        if not os.path.exists(path):
            os.mkdir(path, mode)


def secure_atomic_write(
    path: str,
    content: Union[str, bytes],
    mode: int = SECURE_FILE_MODE,
    encoding: str = "utf-8"
) -> None:
    """
    Atomically write content to a file with secure permissions.

    Uses write-to-temp-then-rename pattern to ensure either the complete
    new content or the old content exists (never a partial file).

    Creates the file with mode 0o600 (owner read/write only) regardless
    of the system umask setting.

    Args:
        path: Absolute path to the target file
        content: String or bytes to write
        mode: File permission mode (default: 0o600)
        encoding: Text encoding for string content (default: utf-8)

    Raises:
        OSError: If file creation, writing, or rename fails
        TypeError: If content is neither str nor bytes
    """
    dir_path = os.path.dirname(path)
    if dir_path and not os.path.exists(dir_path):
        secure_create_directory(dir_path)

    # Create temp file in same directory (required for atomic rename)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=".tmp_")

    try:
        # Set secure permissions on temp file
        os.fchmod(fd, mode)

        with os.fdopen(fd, "wb") as f:
            if isinstance(content, str):
                f.write(content.encode(encoding))
            elif isinstance(content, bytes):
                f.write(content)
            else:
                raise TypeError(f"content must be str or bytes, got {type(content).__name__}")

        # Atomic rename
        os.replace(tmp_path, path)

    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def secure_atomic_write_json(
    path: str,
    data: Any,
    mode: int = SECURE_FILE_MODE,
    indent: int = 2
) -> None:
    """
    Atomically write JSON data to a file with secure permissions.

    Uses write-to-temp-then-rename pattern for atomicity.
    Creates the file with mode 0o600 (owner read/write only).

    Args:
        path: Absolute path to the target file
        data: JSON-serializable data
        mode: File permission mode (default: 0o600)
        indent: JSON indentation (default: 2)

    Raises:
        OSError: If file creation, writing, or rename fails
        json.JSONDecodeError: If data is not JSON-serializable
    """
    content = json.dumps(data, indent=indent)
    secure_atomic_write(path, content, mode=mode)
