"""Subprocess-based Tesseract baseline with word confidence and geometry."""

from __future__ import annotations

import csv
import io
import os
import shutil
import subprocess
from collections import defaultdict
from hashlib import sha256
from pathlib import Path

from PIL import Image

from indicnotice.schemas.document import Document, DocumentBlock, DocumentPage
from indicnotice.schemas.evidence import EvidenceSpan
from services.nlp.ingestion.errors import (
    NoReadableTextError,
    OCRBackendUnavailableError,
    OCRLanguageUnavailableError,
    OCRProcessingError,
)
from services.nlp.ingestion.normalization import normalize_extracted_text
from services.nlp.ingestion.validation import validate_input


class TesseractBackend:
    def __init__(self, executable: str | Path | None = None, *, languages: tuple[str, ...] = ("tel", "hin", "eng"), psm: int = 6):
        self.executable = self._resolve_executable(executable)
        self.languages = languages
        self.psm = psm

    @staticmethod
    def _resolve_executable(executable: str | Path | None) -> str:
        if executable is not None:
            candidate = Path(executable)
            if candidate.is_file():
                return str(candidate.resolve())
            raise OCRBackendUnavailableError(f"Configured Tesseract executable does not exist: {candidate}")
        candidates = [
            os.environ.get("TESSERACT_CMD"),
            shutil.which("tesseract"),
            str(Path.cwd() / ".tools" / "Tesseract-OCR" / "tesseract.exe"),
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                return str(Path(candidate).resolve())
        raise OCRBackendUnavailableError("Tesseract executable was not found; set TESSERACT_CMD or pass executable=.")

    def _run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [self.executable, *arguments],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OCRProcessingError("Tesseract execution failed or timed out.") from exc

    def version(self) -> str:
        result = self._run(["--version"])
        if result.returncode:
            raise OCRProcessingError(result.stderr.strip() or "Tesseract version check failed.")
        return result.stdout.splitlines()[0].strip()

    def available_languages(self) -> set[str]:
        result = self._run(["--list-langs"])
        if result.returncode:
            raise OCRProcessingError(result.stderr.strip() or "Unable to list Tesseract languages.")
        return {line.strip() for line in result.stdout.splitlines() if line.strip() and "available languages" not in line.lower()}

    def _require_languages(self) -> None:
        missing = set(self.languages) - self.available_languages()
        if missing:
            raise OCRLanguageUnavailableError(f"Tesseract language data is missing: {', '.join(sorted(missing))}")

    def extract_page(self, image_path: str | Path, document_id: str, page_number: int = 1) -> tuple[DocumentPage, tuple[EvidenceSpan, ...]]:
        self._require_languages()
        path = Path(image_path).resolve()
        result = self._run([str(path), "stdout", "-l", "+".join(self.languages), "--psm", str(self.psm), "tsv"])
        if result.returncode:
            raise OCRProcessingError(result.stderr.strip() or "Tesseract OCR failed.")
        rows: dict[tuple[int, int, int], list[dict[str, str]]] = defaultdict(list)
        reader = csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
        for row in reader:
            if row.get("level") == "5" and (row.get("text") or "").strip():
                key = (int(row["block_num"]), int(row["par_num"]), int(row["line_num"]))
                rows[key].append(row)
        blocks: list[DocumentBlock] = []
        spans: list[EvidenceSpan] = []
        parts: list[str] = []
        cursor = 0
        for _, words in sorted(rows.items()):
            raw_text = " ".join(word["text"].strip() for word in words)
            text = normalize_extracted_text(raw_text)
            if not text:
                continue
            left = min(int(word["left"]) for word in words)
            top = min(int(word["top"]) for word in words)
            right = max(int(word["left"]) + int(word["width"]) for word in words)
            bottom = max(int(word["top"]) + int(word["height"]) for word in words)
            confidences = [max(0.0, float(word["conf"])) / 100 for word in words if float(word["conf"]) >= 0]
            confidence = sum(confidences) / len(confidences) if confidences else None
            if parts:
                cursor += 1
            start = cursor
            cursor += len(text)
            block_id = f"{document_id}:p{page_number}:b{len(blocks)}"
            bbox = [float(left), float(top), float(right), float(bottom)]
            blocks.append(DocumentBlock(
                block_id=block_id,
                page_number=page_number,
                text=text,
                original_ocr_text=raw_text,
                bbox=bbox,
                block_type="line",
                reading_order=len(blocks),
                confidence=confidence,
            ))
            parts.append(text)
            spans.append(EvidenceSpan(
                evidence_id=f"ev:{block_id}",
                document_id=document_id,
                page_number=page_number,
                text=text,
                original_ocr_text=raw_text,
                bbox=bbox,
                block_id=block_id,
                char_start=start,
                char_end=cursor,
                extraction_method="tesseract",
                confidence=confidence,
            ))
        if not parts:
            raise NoReadableTextError(f"OCR produced no readable text for page {page_number}.")
        with Image.open(path) as image:
            width, height = image.size
        confidences = [block.confidence for block in blocks if block.confidence is not None]
        page = DocumentPage(
            page_number=page_number,
            full_text="\n".join(parts),
            blocks=blocks,
            width_pt=float(width),
            height_pt=float(height),
            extraction_method="tesseract",
            avg_confidence=sum(confidences) / len(confidences) if confidences else None,
        )
        return page, tuple(spans)

    def extract_with_evidence(self, document_path: str) -> tuple[Document, tuple[EvidenceSpan, ...]]:
        validated = validate_input(document_path)
        if not validated.media_type.startswith("image/"):
            raise OCRProcessingError("TesseractBackend accepts PNG/JPEG; PDF page rendering belongs to DocumentIngestor.")
        page, evidence = self.extract_page(validated.path, validated.sha256)
        return Document(
            document_id=validated.sha256,
            source_path=str(validated.path),
            source_type="image",
            pages=[page],
            full_text=page.full_text,
            page_count=1,
            has_embedded_text=False,
            extraction_method="tesseract",
        ), evidence

    def extract(self, document_path: str) -> Document:
        return self.extract_with_evidence(document_path)[0]
