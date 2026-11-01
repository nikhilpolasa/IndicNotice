"""Run the honest, verified-complete NLP-2 evaluation slice.

Image-only fixtures are reported as skipped unless an OCR-backed ingestion run
has already been materialized elsewhere. This script never silently treats
partial annotations as complete gold.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date
import json
from pathlib import Path

from services.nlp.evaluation import aggregate_reports, evaluate_extraction
from services.nlp.extraction.baseline import RegexBaselineExtractor
from services.nlp.ingestion.errors import OCRBackendUnavailableError
from services.nlp.ingestion.router import DocumentIngestor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Optional JSON report destination")
    args = parser.parse_args()
    annotation_path = Path("datasets/annotations/nlp2/v1/annotations.json")
    annotations = json.loads(annotation_path.read_text(encoding="utf-8"))
    reports = []
    skipped: list[dict[str, str]] = []
    for annotation in annotations:
        path = Path(annotation["fixture_path"])
        try:
            ingestion = DocumentIngestor().ingest(path)
        except OCRBackendUnavailableError as exc:
            skipped.append({"fixture_path": path.as_posix(), "reason": str(exc)})
            continue
        analysis = RegexBaselineExtractor().extract_ingestion(ingestion).analysis
        reports.append(evaluate_extraction(analysis, annotation))
    corpus = aggregate_reports(reports)
    payload = {
        "run_date": date.today().isoformat(),
        "annotation_version": "nlp2-gold-v1",
        "evaluated_documents": corpus.document_count,
        "fields": [asdict(item) for item in corpus.fields],
        "errors": [asdict(item) for item in corpus.errors],
        "skipped": skipped,
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
