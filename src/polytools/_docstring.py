"""
Docstring parser — extracts summary and per-parameter descriptions.

Supports three common styles, detected automatically:

    Google style
    ------------
    Summary line.

    Args:
        param1 (str): Description.
        param2: Description spanning
            multiple lines.

    NumPy / SciPy style
    -------------------
    Summary line.

    Parameters
    ----------
    param1 : str
        Description.
    param2 : int, optional
        Description.

    reStructuredText (Sphinx) style
    --------------------------------
    Summary line.

    :param param1: Description.
    :param param2: Description.

Pure Python stdlib only — no third-party parsers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class DocstringInfo:
    """Parsed information from a docstring."""

    summary: str = ""
    """First non-empty paragraph of the docstring."""

    params: dict[str, str] = field(default_factory=dict)
    """Mapping of parameter name → description string."""

    returns: str = ""
    """Description of the return value, if present."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_summary(lines: list[str]) -> str:
    """Return the first non-empty paragraph as a single string."""
    parts: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            parts.append(stripped)
        elif parts:
            break
    return " ".join(parts)


def _dedent_block(lines: list[str]) -> list[str]:
    """Remove common leading whitespace from a block of lines."""
    # Find minimum non-zero indent
    indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
    if not indents:
        return lines
    min_indent = min(indents)
    return [l[min_indent:] if len(l) >= min_indent else l.lstrip() for l in lines]


# ---------------------------------------------------------------------------
# Google style parser
# ---------------------------------------------------------------------------

_GOOGLE_SECTION_RE = re.compile(
    r"^(Args|Arguments|Parameters|Params|Keyword Args|Keyword Arguments)\s*:\s*$",
    re.IGNORECASE,
)
_GOOGLE_RETURN_RE = re.compile(r"^(Returns?|Yields?)\s*:\s*$", re.IGNORECASE)
_GOOGLE_OTHER_SECTION_RE = re.compile(r"^\w[\w ]*:\s*$")

# Matches:  name (type): description
#        OR name: description
_GOOGLE_PARAM_RE = re.compile(
    r"^(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)"
)


def _parse_google(lines: list[str]) -> DocstringInfo:
    info = DocstringInfo(summary=_extract_summary(lines))

    in_args = False
    in_returns = False
    param_indent: int | None = None
    current_param: str | None = None
    current_desc: list[str] = []

    def _flush() -> None:
        nonlocal current_param, current_desc
        if current_param is not None:
            info.params[current_param] = " ".join(current_desc).strip()
            current_param = None
            current_desc = []

    for line in lines:
        stripped = line.strip()

        # Detect section headers
        if _GOOGLE_SECTION_RE.match(stripped):
            _flush()
            in_args = True
            in_returns = False
            param_indent = None
            continue

        if _GOOGLE_RETURN_RE.match(stripped):
            _flush()
            in_args = False
            in_returns = True
            continue

        # Other known section header → exit args/returns
        if _GOOGLE_OTHER_SECTION_RE.match(stripped) and not stripped.startswith(" "):
            _flush()
            in_args = False
            in_returns = False
            continue

        if in_args:
            if not stripped:
                # Blank line: finalize current param but stay in section
                _flush()
                continue

            indent = len(line) - len(line.lstrip())

            if param_indent is None:
                param_indent = indent

            if indent == param_indent:
                # New parameter line
                _flush()
                m = _GOOGLE_PARAM_RE.match(stripped)
                if m:
                    current_param = m.group(1)
                    rest = m.group(2).strip()
                    current_desc = [rest] if rest else []
            elif indent > param_indent and current_param is not None:
                # Continuation of previous param description
                current_desc.append(stripped)

        elif in_returns:
            if stripped:
                info.returns += (" " if info.returns else "") + stripped

    _flush()
    return info


# ---------------------------------------------------------------------------
# NumPy style parser
# ---------------------------------------------------------------------------

_NUMPY_DASH_RE = re.compile(r"^-{3,}\s*$")
_NUMPY_PARAM_HEADER_RE = re.compile(
    r"^(Parameters|Params|Arguments|Args)\s*$", re.IGNORECASE
)
_NUMPY_RETURNS_HEADER_RE = re.compile(r"^(Returns|Yields)\s*$", re.IGNORECASE)
# Matches:  name : type, optional
#        OR name
_NUMPY_PARAM_RE = re.compile(r"^(\w+)\s*(?::\s*.*)?\s*$")


def _parse_numpy(lines: list[str]) -> DocstringInfo:
    info = DocstringInfo(summary=_extract_summary(lines))

    in_params = False
    in_returns = False
    current_param: str | None = None
    current_desc: list[str] = []

    # Tracks the indentation of parameter *name* lines within the section.
    # The first non-empty line after the dashes sets this anchor.
    param_name_indent: int | None = None

    def _flush() -> None:
        nonlocal current_param, current_desc
        if current_param is not None:
            info.params[current_param] = " ".join(current_desc).strip()
            current_param = None
            current_desc = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        next_stripped = lines[i + 1].strip() if i + 1 < len(lines) else ""

        # Section header detection: "Parameters" followed by "---..." on next line
        if _NUMPY_PARAM_HEADER_RE.match(stripped) and _NUMPY_DASH_RE.match(next_stripped):
            _flush()
            in_params = True
            in_returns = False
            param_name_indent = None
            i += 2  # skip header + dashes
            continue

        if _NUMPY_RETURNS_HEADER_RE.match(stripped) and _NUMPY_DASH_RE.match(next_stripped):
            _flush()
            in_params = False
            in_returns = True
            i += 2
            continue

        # Any other section header (word + underline) → exit current section
        if stripped and _NUMPY_DASH_RE.match(next_stripped) and (in_params or in_returns):
            _flush()
            in_params = False
            in_returns = False
            i += 2
            continue

        if in_params:
            if not stripped:
                # Blank lines are allowed between params; flush current
                _flush()
                i += 1
                continue

            indent = len(line) - len(line.lstrip())

            # First non-empty content line sets the anchor indent for param names
            if param_name_indent is None:
                param_name_indent = indent

            if indent == param_name_indent:
                # This is a parameter name line: "name : type" or just "name"
                m = _NUMPY_PARAM_RE.match(stripped)
                if m:
                    _flush()
                    current_param = m.group(1)
            elif indent > param_name_indent and current_param is not None:
                # Indented further → description line for the current param
                current_desc.append(stripped)

        elif in_returns and stripped:
            info.returns += (" " if info.returns else "") + stripped

        i += 1

    _flush()
    return info


# ---------------------------------------------------------------------------
# reStructuredText style parser
# ---------------------------------------------------------------------------

_RST_PARAM_RE = re.compile(r":param\s+(?:\w+\s+)?(\w+)\s*:\s*(.*)")
_RST_RETURNS_RE = re.compile(r":returns?\s*:\s*(.*)")


def _parse_rst(lines: list[str]) -> DocstringInfo:
    info = DocstringInfo(summary=_extract_summary(lines))

    current_param: str | None = None
    current_desc: list[str] = []

    def _flush() -> None:
        nonlocal current_param, current_desc
        if current_param is not None:
            info.params[current_param] = " ".join(current_desc).strip()
            current_param = None
            current_desc = []

    for line in lines:
        stripped = line.strip()

        m_param = _RST_PARAM_RE.match(stripped)
        if m_param:
            _flush()
            current_param = m_param.group(1)
            current_desc = [m_param.group(2).strip()]
            continue

        m_ret = _RST_RETURNS_RE.match(stripped)
        if m_ret:
            _flush()
            info.returns = m_ret.group(1).strip()
            continue

        # Continuation: indented line belonging to current :param
        if current_param and stripped and line.startswith("   "):
            current_desc.append(stripped)
            continue

        # New RST field of a different type → flush
        if stripped.startswith(":") and current_param:
            _flush()

    _flush()
    return info


# ---------------------------------------------------------------------------
# Auto-detect and dispatch
# ---------------------------------------------------------------------------

def parse_docstring(doc: str | None) -> DocstringInfo:
    """Parse a docstring and return extracted summary + param descriptions.

    Tries Google → NumPy → RST in order. The first style that yields any
    parameter descriptions wins. Falls back to extracting the summary only.

    Parameters
    ----------
    doc : str | None
        Raw docstring text (typically obtained via ``inspect.getdoc()``).

    Returns
    -------
    DocstringInfo
        Parsed metadata.
    """
    if not doc:
        return DocstringInfo()

    lines = doc.splitlines()

    # Try each style; accept the first that extracts any params
    for parser in (_parse_google, _parse_numpy, _parse_rst):
        result = parser(lines)
        if result.params:
            return result

    # No params found in any style — at minimum return the summary
    return DocstringInfo(summary=_extract_summary(lines))
