"""JavaScript utilities for safe code execution."""

import json
from typing import Any


def sanitize_js_string(value: str) -> str:
    """Sanitize string for safe JavaScript injection.

    Escapes special characters to prevent injection attacks.

    Args:
        value: String to sanitize

    Returns:
        Sanitized string safe for JavaScript

    Examples:
        >>> sanitize_js_string("alert('XSS')")
        "alert(\\'XSS\\')"
    """
    if not isinstance(value, str):
        value = str(value)

    # Escape special characters
    replacements = {
        "\\": "\\\\",  # Backslash first
        "'": "\\'",
        '"': '\\"',
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
        "\b": "\\b",
        "\f": "\\f",
        "<": "\\x3C",  # Prevent </script> injection
        ">": "\\x3E",
        "&": "\\x26",
    }

    for char, escape in replacements.items():
        value = value.replace(char, escape)

    return value


def build_js_args(*args: Any) -> str:
    """Build JavaScript function arguments safely.

    Converts Python values to JavaScript-safe representations.

    Args:
        *args: Arguments to convert

    Returns:
        JavaScript argument string

    Examples:
        >>> build_js_args("test", 123, True, None)
        "'test', 123, true, null"
    """
    js_args = []

    for arg in args:
        if arg is None:
            js_args.append("null")
        elif isinstance(arg, bool):
            js_args.append("true" if arg else "false")
        elif isinstance(arg, int | float):
            js_args.append(str(arg))
        elif isinstance(arg, str):
            js_args.append(f"'{sanitize_js_string(arg)}'")
        elif isinstance(arg, list | dict):
            # Use JSON for complex types
            js_args.append(json.dumps(arg))
        else:
            # Convert to string and sanitize
            js_args.append(f"'{sanitize_js_string(str(arg))}'")

    return ", ".join(js_args)


def wrap_js_function(code: str, *args: Any) -> str:
    """Wrap JavaScript code in an IIFE with arguments.

    Creates an Immediately Invoked Function Expression for isolation.

    Args:
        code: JavaScript code to wrap
        *args: Arguments to pass to the function

    Returns:
        Wrapped JavaScript code

    Examples:
        >>> wrap_js_function("return x + y;", 1, 2)
        "(function(x, y) { return x + y; })(1, 2)"
    """
    arg_names = [f"arg{i}" for i in range(len(args))]
    arg_list = ", ".join(arg_names)
    arg_values = build_js_args(*args)

    return f"(function({arg_list}) {{ {code} }})({arg_values})"


def escape_css_selector(selector: str) -> str:
    """Escape special characters in CSS selector.

    Args:
        selector: CSS selector to escape

    Returns:
        Escaped CSS selector
    """
    # CSS special characters that need escaping
    special_chars = r'!"#$%&\'()*+,./:;<=>?@[\]^`{|}~'

    for char in special_chars:
        selector = selector.replace(char, f"\\{char}")

    return selector
