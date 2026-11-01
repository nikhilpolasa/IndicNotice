"""Benchmark uncached initial extraction and personalized matching on real PDFs."""
from __future__ import annotations

import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from demo.product import initial_analysis
from services.auth.notices import NoticeLibrary, evaluate_notice
from services.auth.store import AuthStore

FIXTURES = {
    "hindi_scert": ROOT / "datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf",
    "telugu_kvs_mixed_english": ROOT / "datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf",
}
PASSWORD = "Benchmark Operator Passphrase 832!"


def main() -> None:
    result: dict = {"cache_policy": "Each analysis invocation calls initial_analysis directly; no session cache is used.",
                    "enrichment": "Optional AI enrichment was not requested; these timings cover native PDF extraction and deterministic baseline/semantic analysis.",
                    "fixtures": {}}
    analyses = {}
    for name, path in FIXTURES.items():
        pdf = path.read_bytes()
        samples = []
        for label in ("cold", "warm"):
            started = time.perf_counter()
            analyses[name] = initial_analysis(pdf, path.name)
            samples.append({"run": label, "elapsed_seconds": round(time.perf_counter() - started, 6),
                            "cached": False})
        result["fixtures"][name] = {
            "path": path.relative_to(ROOT).as_posix(), "bytes": len(pdf),
            "source_language": analyses[name].analysis.source_language,
            "analysis_runs": samples,
            "meets_10_second_target": all(item["elapsed_seconds"] < 10 for item in samples),
        }

    with tempfile.TemporaryDirectory(prefix="indicnotice-match-benchmark-") as temp:
        store = AuthStore(Path(temp) / "accounts.sqlite3")
        admin = store.register("operator@example.test", PASSWORD)
        store.grant_admin(admin["email"], PASSWORD)
        library = NoticeLibrary(store)
        published = []
        for name, path in FIXTURES.items():
            item = analyses[name]
            draft = library.create_draft(admin["account_id"], path.read_bytes(), item.analysis)
            library.set_publication(admin["account_id"], draft.notice_id, True)
            published.append(library.get_for_account(admin["account_id"], draft.notice_id))
        profile = {"marks_percentage": 80, "current_class": 8, "previous_class": 7,
                   "current_school_type": "government", "previous_school_type": "government",
                   "annual_family_income_inr": 200000, "attempt_count": 1}
        samples = []
        for _ in range(100):
            start = time.perf_counter()
            outcomes = [evaluate_notice(notice, profile).status for notice in published]
            samples.append(time.perf_counter() - start)
        ordered = sorted(samples)
        result["matching"] = {
            "published_real_fixture_count": len(published), "notices_per_match": len(published),
            "iterations": len(samples), "status_each_iteration": outcomes,
            "total_elapsed_seconds": round(sum(samples), 6),
            "mean_seconds_per_two_notice_match": round(statistics.mean(samples), 6),
            "p95_seconds_per_two_notice_match": round(ordered[int(.95 * (len(ordered) - 1))], 6),
            "median_seconds_per_two_notice_match": round(statistics.median(samples), 6),
            "cache_policy": "No match-result cache; each iteration re-evaluates both published analyses against the profile.",
        }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
