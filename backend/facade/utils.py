"""Utility functions for facade controllers."""

import json
from typing import Any


def sanitize_js_string(value: str) -> str:
    """Sanitize a string for safe inclusion in JavaScript code.

    This prevents JavaScript injection attacks by properly escaping
    special characters.

    Args:
        value: The string to sanitize

    Returns:
        str: The sanitized string safe for JavaScript inclusion
    """
    if not isinstance(value, str):
        return str(value)

    # Escape special characters
    return (
        value.replace("\\", "\\\\")  # Backslash must be first
        .replace("'", "\\'")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("\b", "\\b")
        .replace("\f", "\\f")
        .replace("</", "<\\/")  # Prevent script tag closing
    )


def build_js_function_call(func_name: str, *args: Any) -> str:
    """Build a safe JavaScript function call with proper argument escaping.

    Args:
        func_name: The JavaScript function name
        *args: Arguments to pass to the function

    Returns:
        str: Safe JavaScript code string
    """
    # Convert arguments to JavaScript-safe format
    js_args = []
    for arg in args:
        if isinstance(arg, str):
            js_args.append(f"'{sanitize_js_string(arg)}'")
        elif isinstance(arg, bool):
            js_args.append("true" if arg else "false")
        elif isinstance(arg, int | float):
            js_args.append(str(arg))
        elif arg is None:
            js_args.append("null")
        elif isinstance(arg, list | dict):
            # Use JSON for complex objects
            js_args.append(json.dumps(arg))
        else:
            js_args.append(f"'{sanitize_js_string(str(arg))}'")

    return f"{func_name}({', '.join(js_args)})"


def safe_js_property_access(obj: str, property_path: str) -> str:
    """Build safe JavaScript property access with injection prevention.

    Args:
        obj: The JavaScript object name
        property_path: The property path (e.g., "style.display")

    Returns:
        str: Safe JavaScript property access string
    """
    # Validate object name (alphanumeric and underscore only)
    if not obj.replace("_", "").isalnum():
        raise ValueError(f"Invalid JavaScript object name: {obj}")

    # Split and validate property path
    parts = property_path.split(".")
    safe_parts = []

    for part in parts:
        # Allow alphanumeric, underscore, and array notation
        if part.endswith("]") and "[" in part:
            # Handle array access like "items[0]"
            prop, index = part.split("[", 1)
            index = index.rstrip("]")

            # Validate property name
            if not prop.replace("_", "").isalnum():
                raise ValueError(f"Invalid property name: {prop}")

            # Validate index
            if not index.isdigit():
                raise ValueError(f"Invalid array index: {index}")

            safe_parts.append(f"{prop}[{index}]")
        else:
            # Regular property
            if not part.replace("_", "").isalnum():
                raise ValueError(f"Invalid property name: {part}")
            safe_parts.append(part)

    return f"{obj}.{'.'.join(safe_parts)}"


def parameterized_js_execution(template: str, **params: Any) -> str:
    """Build JavaScript code from a template with parameterized values.

    This is the safest way to build JavaScript code as it prevents
    injection by properly escaping all parameters.

    Args:
        template: JavaScript template with {param_name} placeholders
        **params: Parameters to substitute into the template

    Returns:
        str: Safe JavaScript code with substituted parameters

    Example:
        >>> parameterized_js_execution(
        ...     "document.querySelector({selector}).innerHTML = {content}",
        ...     selector="#myDiv",
        ...     content="<h1>Hello</h1>"
        ... )
        "document.querySelector('#myDiv').innerHTML = '<h1>Hello</h1>'"
    """
    safe_params = {}

    for key, value in params.items():
        if isinstance(value, str):
            safe_params[key] = f"'{sanitize_js_string(value)}'"
        elif isinstance(value, bool):
            safe_params[key] = "true" if value else "false"
        elif isinstance(value, int | float):
            safe_params[key] = str(value)
        elif value is None:
            safe_params[key] = "null"
        elif isinstance(value, list | dict):
            safe_params[key] = json.dumps(value)
        else:
            safe_params[key] = f"'{sanitize_js_string(str(value))}'"

    return template.format(**safe_params)
