"""
Custom Exception Hierarchy for the MPLA System.

This module defines a set of custom exception classes to provide more
specific and informative error handling throughout the application. Instead of
raising generic `Exception` or `ValueError`, using these exceptions makes
the agent's failure modes more explicit and easier to debug.
"""

class MPLAError(Exception):
    """Base class for all custom exceptions in the MPLA system."""
    pass

# --- Configuration Errors ---
class ConfigurationError(MPLAError):
    """Raised for errors related to loading or validating configuration."""
    def __init__(self, message="Configuration error"):
        self.message = message
        super().__init__(self.message)

# --- Knowledge Base Errors ---
class KnowledgeBaseError(MPLAError):
    """Raised for errors related to the Knowledge Base."""
    pass

class RecordNotFoundError(KnowledgeBaseError):
    """Raised when a specific record is not found in the KB."""
    def __init__(self, model: str, record_id: int):
        self.message = f"Record of type '{model}' with ID '{record_id}' not found."
        super().__init__(self.message)

# --- Orchestrator Errors ---
class OrchestratorError(MPLAError):
    """Raised for errors during AI model deployment and interaction."""
    pass

class APIConnectionError(OrchestratorError):
    """Raised for network-related errors when connecting to an AI API."""
    pass

class APITimeoutError(APIConnectionError):
    """Raised when an API request times out."""
    pass

class APIResponseError(OrchestratorError):
    """Raised for invalid or unexpected responses from the AI API."""
    def __init__(self, message="Invalid response from AI API", status_code=None):
        self.message = message
        self.status_code = status_code
        super().__init__(f"{self.message} (Status: {self.status_code})" if self.status_code else self.message)

# --- Agent/Module Errors ---
class EnhancementError(MPLAError):
    """Raised for errors during the prompt enhancement phase."""
    pass

class EvaluationError(MPLAError):
    """Raised for errors during the evaluation phase."""
    pass 