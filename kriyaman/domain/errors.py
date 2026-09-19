"""Domain exception definitions for Kriyamaan."""


class KriyamanError(Exception):
    """Base error for all Kriyamaan domain exceptions."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class BudgetExceededError(KriyamanError):
    """Raised when an execution budget limit is reached."""

    def __init__(self, message: str, budget_name: str, limit: int | float, actual: int | float):
        super().__init__(message, code="BUDGET_EXCEEDED")
        self.budget_name = budget_name
        self.limit = limit
        self.actual = actual


class PolicyViolationError(KriyamanError):
    """Raised when an action violates safety or architectural policy."""

    def __init__(self, message: str, policy_name: str):
        super().__init__(message, code="POLICY_VIOLATION")
        self.policy_name = policy_name


class EvidenceSufficiencyError(KriyamanError):
    """Raised when evidence sufficiency invariant is violated."""

    def __init__(self, message: str):
        super().__init__(message, code="EVIDENCE_INSUFFICIENT")


class ProviderError(KriyamanError):
    """Raised when an external or adapter provider encounters an unhandled error."""

    def __init__(self, message: str, provider_name: str, is_transient: bool = False):
        super().__init__(message, code="PROVIDER_ERROR")
        self.provider_name = provider_name
        self.is_transient = is_transient


class ValidationError(KriyamanError):
    """Raised on invalid input or schema violation."""

    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")


class ToolExecutionError(KriyamanError):
    """Raised when tool invocation fails."""

    def __init__(self, message: str, tool_name: str):
        super().__init__(message, code="TOOL_EXECUTION_ERROR")
        self.tool_name = tool_name


class ResourceNotFoundError(KriyamanError):
    """Raised when a requested resource (session, document, run, etc.) is not found."""

    def __init__(self, message: str, resource_type: str = "resource", resource_id: str | None = None):
        super().__init__(message, code="RESOURCE_NOT_FOUND")
        self.resource_type = resource_type
        self.resource_id = resource_id


