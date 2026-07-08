class FlowScriptError(Exception):
    """Base error for FlowScript runtime failures."""


class PlanValidationError(FlowScriptError):
    """Raised when a flow is structurally invalid."""


class ToolExecutionError(FlowScriptError):
    """Raised when a local tool call fails."""


class ModelProtocolError(FlowScriptError):
    """Raised when the model response cannot be normalized."""


class UnsupportedTerminalError(FlowScriptError):
    """Raised when the validation-only runtime reaches an unsupported terminal."""
