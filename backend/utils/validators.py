"""
Source code validator.
Performs AST-based syntax validation and basic sanity checks.
"""
import ast
import os
from typing import Tuple, List, Dict

from config import MAX_CODE_SIZE_BYTES


def validate_source_code(code: str) -> Tuple[bool, List[Dict]]:
    """
    Validate Python source code for syntax errors.

    Returns (is_valid, errors) where errors is a list of dicts with
    keys: line, column, message.
    """
    errors = []

    if not code or not code.strip():
        errors.append({"line": 0, "column": 0, "message": "Source code is empty"})
        return False, errors

    if len(code.encode("utf-8")) > MAX_CODE_SIZE_BYTES:
        errors.append({
            "line": 0,
            "column": 0,
            "message": (
                f"Source code exceeds the maximum allowed size of "
                f"{MAX_CODE_SIZE_BYTES // 1024} KB"
            ),
        })
        return False, errors

    try:
        ast.parse(code)
    except SyntaxError as exc:
        errors.append({
            "line": exc.lineno or 0,
            "column": exc.offset or 0,
            "message": str(exc.msg),
        })
        return False, errors
    except ValueError as exc:
        errors.append({"line": 0, "column": 0, "message": str(exc)})
        return False, errors

    return True, []


def validate_filename(filename: str) -> Tuple[bool, str]:
    """
    Validate an uploaded filename for safety.

    Returns (is_valid, reason).
    """
    if not filename:
        return False, "Filename is empty"
    # Reject path traversal
    basename = os.path.basename(filename)
    if basename != filename:
        return False, "Path traversal detected in filename"
    if ".." in filename:
        return False, "Path traversal detected"
    if not filename.endswith(".py"):
        return False, "Only .py files are accepted"
    if len(filename) > 128:
        return False, "Filename is too long"
    # Allow alphanumeric, underscore, hyphen, dot
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")
    if not all(c in allowed for c in basename):
        return False, "Filename contains invalid characters"
    return True, ""
