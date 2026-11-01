"""Reproducible real-upload benchmarks; does not read evaluation annotations."""
from __future__ import annotations
import time
PROCESS_STARTED = time.perf_counter()
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def worker(path):
    from demo.product import session_analysis
    payload = Path(path).read_bytes()
    state = {}
    result, _, cold = session_analysis(state, payload, Path(path).name)
    process_cold = time.perf_counter() - PROCESS_STARTED
    _, _, cached = session_analysis(state, payload, Path(path).name)
    _, _, warm = session_analysis({}, payload, Path(path).name)
    return {"pdf": Path(path).as_posix(), "process_cold_seconds": process_cold,
            "initial_seconds": cold, "warm_uncached_seconds": warm,
            "session_cache_seconds": cached, "pages": result.ingestion.document.page_count,
            "routes": [r.method for r in result.ingestion.routes],
            "dates": len(result.analysis.dates), "fees": len(result.analysis.fees),
            "documents": len(result.analysis.required_documents),
            "eligibility_extracted": result.analysis.eligibility is not None,
            "advanced_review": "not run"}


def main():
    import pymupdf
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker")
    parser.add_argument("--output", default="reports/product_benchmarks.json")
    parser.add_argument("--include-ocr", action="store_true")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker)))
        return
    records = []
    excluded = []
    for pdf in sorted((ROOT / "datasets/fixtures/nlp2").rglob("*.pdf")):
        with pymupdf.open(pdf) as document:
            if not args.include_ocr and any(len(page.get_text().strip()) < 20 for page in document):
                excluded.append({"pdf": str(pdf), "reason": "contains a page requiring OCR; excluded from native-text latency target"})
                continue
        run = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", str(pdf)],
                             capture_output=True, text=True, check=True, cwd=ROOT)
        records.append(json.loads(run.stdout))
    Path(args.output).write_text(json.dumps({"method": "initial rules + evidence-gated semantic extraction; no model calls", "documents": records, "excluded": excluded}, indent=2), encoding="utf-8")
    print(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
