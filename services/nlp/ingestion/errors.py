"""Typed, user-safe failures raised by the ingestion boundary."""


class IngestionError(Exception):
    """Base class for expected document-ingestion failures."""


class DocumentNotFoundError(IngestionError):
    pass


class UnsupportedDocumentTypeError(IngestionError):
    pass


class FileSignatureMismatchError(IngestionError):
    pass


class EmptyDocumentError(IngestionError):
    pass


class DocumentTooLargeError(IngestionError):
    pass


class PageLimitExceededError(IngestionError):
    pass


class CorruptDocumentError(IngestionError):
    pass


class EncryptedPDFError(IngestionError):
    pass


class OCRBackendUnavailableError(IngestionError):
    pass


class OCRLanguageUnavailableError(IngestionError):
    pass


class OCRProcessingError(IngestionError):
    pass


class NoReadableTextError(IngestionError):
    pass
