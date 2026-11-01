"""Run real NLP-3 inference and an independent NLP-2/NLP-3 comparison.

This script intentionally requires an already running model endpoint. Unit tests
never invoke it. The default fixtures are one genuine Hindi notice and one
genuine Telugu notice that both pass through canonical NLP-1 ingestion.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
from typing import Any

from services.nlp.evaluation import aggregate_reports, evaluate_extraction
from services.nlp.evaluation.contextual_metrics import grounding_metrics
from services.nlp.extraction.baseline import RegexBaselineExtractor
from services.nlp.extraction.contextual import ContextualStructuredExtractor, HTTPChatProvider
from services.nlp.extraction.contextual.types import ModelRequest, ModelResponse, StructuredModelProvider
from services.nlp.ingestion.router import DocumentIngestor


DEFAULT_FIXTURES = (
    "datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf",
    "datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf",
)


class CheckpointingProvider:
    """Persist successful public-fixture responses by exact request/settings hash."""

    def __init__(
        self,
        inner: StructuredModelProvider,
        cache_dir: Path,
        settings: dict[str, Any],
    ) -> None:
        self.inner = inner
        self.cache_dir = cache_dir
        self.settings = settings
        self.hits = 0
        self.misses = 0

    @property
    def model_id(self) -> str:
        return self.inner.model_id

    def complete(self, request: ModelRequest) -> ModelResponse:
        identity = json.dumps(
            {
                "protocol": 1,
                "model_id": self.model_id,
                "settings": self.settings,
                "messages": request.messages,
                "response_schema": request.response_schema,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        cache_path = self.cache_dir / f"{sha256(identity).hexdigest()}.json"
        if cache_path.exists():
            self.hits += 1
            value = json.loads(cache_path.read_text(encoding="utf-8"))
            return ModelResponse(**value["response"])
        response = self.inner.complete(request)
        self.misses += 1
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "source": "genuine model response",
                    "model_id": self.model_id,
                    "settings": self.settings,
                    "response": asdict(response),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return response


def _gpu() -> dict[str, Any] | None:
    try:
        output = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,driver_version",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    name, total, used, driver = [item.strip() for item in output.split(",", 3)]
    return {
        "name": name,
        "memory_total_mib": int(total),
        "memory_used_mib": int(used),
        "driver_version": driver,
    }


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18089")
    parser.add_argument("--model-id", default="Qwen3-4B-Q4_K_M")
    parser.add_argument("--output", default="reports/nlp3_real_evaluation.json")
    parser.add_argument("--fixture", action="append", dest="fixtures")
    parser.add_argument("--max-chunk-chars", type=int, default=3_000)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--cache-dir", default=".tmp/nlp3_response_cache")
    args = parser.parse_args()

    annotation_path = Path("datasets/annotations/nlp2/v1/annotations.json")
    annotations = json.loads(annotation_path.read_text(encoding="utf-8"))
    by_fixture = {item["fixture_path"]: item for item in annotations}
    fixtures = tuple(args.fixtures or DEFAULT_FIXTURES)
    decoding = {
        "temperature": 0.2,
        "top_p": 0.8,
        "presence_penalty": 1.5,
        "seed": 42,
        "max_tokens": 4096,
    }
    http_provider = HTTPChatProvider(
        base_url=args.base_url,
        model_id=args.model_id,
        **decoding,
    )
    provider = CheckpointingProvider(
        http_provider,
        Path(args.cache_dir),
        {
            **decoding,
            "prompt_version": "indicnotice-contextual-v1",
            "max_chunk_chars": args.max_chunk_chars,
        },
    )
    contextual = ContextualStructuredExtractor(
        provider,
        max_chunk_chars=args.max_chunk_chars,
        timeout_seconds=args.timeout,
    )
    baseline = RegexBaselineExtractor()
    records: list[dict[str, Any]] = []
    baseline_reports = []
    contextual_reports = []
    for fixture in fixtures:
        annotation = by_fixture[fixture]
        ingestion = DocumentIngestor().ingest(Path(fixture))
        baseline_analysis = baseline.extract_ingestion(ingestion).analysis
        contextual_result = contextual.extract_ingestion(ingestion)
        baseline_report = evaluate_extraction(baseline_analysis, annotation)
        contextual_report = evaluate_extraction(contextual_result.analysis, annotation)
        baseline_reports.append(baseline_report)
        contextual_reports.append(contextual_report)
        records.append(
            {
                "fixture_path": fixture,
                "document_id": ingestion.document.document_id,
                "language": annotation["language"],
                "routes": [asdict(item) for item in ingestion.routes],
                "nlp2": {
                    "analysis": baseline_analysis.model_dump(mode="json"),
                    "evaluation": asdict(baseline_report),
                },
                "nlp3": {
                    "analysis": contextual_result.analysis.model_dump(mode="json"),
                    "evaluation": asdict(contextual_report),
                    "grounding": asdict(grounding_metrics(contextual_result.analysis, contextual_result.diagnostics)),
                    "diagnostics": asdict(contextual_result.diagnostics),
                },
            }
        )

    baseline_corpus = aggregate_reports(baseline_reports)
    contextual_corpus = aggregate_reports(contextual_reports)
    model_path = Path(".tools/models/Qwen3-4B-Q4_K_M.gguf")
    payload = {
        "milestone": "NLP-3",
        "run_date": date.today().isoformat(),
        "annotation_version": "nlp2-gold-v1",
        "comparison_independence": "NLP-2 and NLP-3 consume the same NLP-1 ingestion result; NLP-3 never consumes NLP-2 output or rules.",
        "limitations": "Only verified_complete annotation fields are scored; this is a two-document smoke comparison, not a corpus-quality claim.",
        "model": {
            "repository": "Qwen/Qwen3-4B-GGUF",
            "revision": "bc640142c66e1fdd12af0bd68f40445458f3869b",
            "file": "Qwen3-4B-Q4_K_M.gguf",
            "sha256": _sha256(model_path),
            "provider_model_id": args.model_id,
            "quantization": "Q4_K_M",
            "license": "Apache-2.0",
        },
        "runtime": {
            "provider": "llama.cpp local OpenAI-style HTTP",
            "llama_cpp": "b11429 / commit d81235049384534c167caea52b85a694f6103d14",
            "endpoint": args.base_url,
            "context_size": 16_384,
            "max_chunk_chars": args.max_chunk_chars,
            "max_output_tokens": 4096,
            "temperature": 0.2,
            "top_p": 0.8,
            "presence_penalty": 1.5,
            "seed": 42,
            "reasoning": "off",
            "gpu_layers": "all",
            "flash_attention": "auto",
            "python": platform.python_version(),
            "platform": platform.platform(),
            "gpu_after_run": _gpu(),
            "checkpoint_cache": {
                "directory": args.cache_dir,
                "hits": provider.hits,
                "genuine_inference_misses": provider.misses,
            },
        },
        "nlp2_corpus": asdict(baseline_corpus),
        "nlp3_corpus": asdict(contextual_corpus),
        "documents": records,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": output_path.as_posix(),
        "documents": len(records),
        "nlp2_fields": [asdict(item) for item in baseline_corpus.fields],
        "nlp3_fields": [asdict(item) for item in contextual_corpus.fields],
        "nlp3_grounding": [record["nlp3"]["grounding"] for record in records],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
