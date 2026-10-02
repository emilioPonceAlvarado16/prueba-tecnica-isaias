class ToolError(Exception):
    """Falla técnica de un tool (timeout, 5xx). El executor reintenta según core.tool."""


class ToolTimeout(ToolError):
    pass


class ToolUnavailable(ToolError):
    pass


class ToolDenied(Exception):
    """El agente intentó usar un tool fuera de su allowlist."""
