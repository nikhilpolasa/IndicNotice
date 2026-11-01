"""Capture mixed-language answers from checked-in Hindi/Telugu notice PDFs."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from demo.product import initial_analysis
from demo.questions import answer_notice

CASES = [
    ("hindi_scert", "datasets/fixtures/nlp2/hindi/scert_haryana_nmmss_2025_hindi.pdf",
     "దరఖాస్తు deadline ఏమిటి?", "te"),
    ("telugu_kvs", "datasets/fixtures/nlp2/telugu/kv_kadapa_admission_2025_telugu.pdf",
     "आवेदन deadline क्या है?", "hi"),
]


def main():
    rows = []
    for name, relative_path, question, language in CASES:
        path = ROOT / relative_path
        result = initial_analysis(path.read_bytes(), path.name)
        answer = answer_notice(question, result, language=language)
        rows.append({
            "document": name, "language": language, "kind": "mixed",
            "question": question, "answer": answer.answer_text,
            "answerability": answer.answerability.value, "abstained": answer.abstained,
            "citation_pages": [citation.page_number for citation in answer.citations],
        })
    output = ROOT / "reports" / "notifications_mixed_qa.json"
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
