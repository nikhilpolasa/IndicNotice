"""Typed failures for contextual structured extraction."""


class StructuredExtractionError(RuntimeError):
    """Base class for NLP-3 extraction failures."""


class ProviderUnavailable(StructuredExtractionError):
    """The configured model provider cannot be reached or used."""


class ProviderTimeout(StructuredExtractionError):
    """The provider exceeded the configured request deadline."""


class SchemaValidationFailure(StructuredExtractionError):
    """Model output remained invalid after the bounded repair attempt."""


class EvidenceValidationFailure(StructuredExtractionError):
    """Model output referenced missing or unsupported evidence."""


class ContextTooLarge(StructuredExtractionError):
    """A provenance unit cannot be sent without truncation."""
