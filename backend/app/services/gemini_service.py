# Re-export from ai_service for backwards compatibility.
# All logic has moved to ai_service.py which supports both Claude and Gemini.
from backend.app.services.ai_service import (
    AIService,
    ContractExtraction,
    InvoiceExtraction,
    LineItemExtraction,
    ReportExtraction,
    ValidationResult,
    gemini_service,
)

__all__ = [
    "AIService",
    "InvoiceExtraction",
    "ContractExtraction",
    "ReportExtraction",
    "ValidationResult",
    "LineItemExtraction",
    "gemini_service",
]
