"""NLP-1 document ingestion public API."""

from services.nlp.ingestion.router import DocumentIngestor
from services.nlp.ingestion.quality import TextQualityDiagnostics, diagnose_text_quality
from services.nlp.ingestion.types import IngestionResult, PageRoute

__all__ = ["DocumentIngestor", "IngestionResult", "PageRoute", "TextQualityDiagnostics", "diagnose_text_quality"]
