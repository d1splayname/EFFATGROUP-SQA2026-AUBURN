import json
import re
from pathlib import Path
from typing import Any, Optional, Dict, List


ROOT = Path(__file__).resolve().parents[2]
INDIVIDUAL_DIR = ROOT / "individual"

INPUT_FILE = INDIVIDUAL_DIR / "input" / "selected_requirements_llm.json"
MISTRAL_FILE = INDIVIDUAL_DIR / "output" / "mistral_api_test_cases.json"
QUANT_FILE = INDIVIDUAL_DIR / "output" / "mistral_quantized_test_cases.json"
OUTPUT_FILE = INDIVIDUAL_DIR / "output" / "comparison_report.json"

REQUIRED_FIELDS = [
    "test_case_id",
    "requirement_id",
    "description",
    "input_data",
    "expected_output",
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def tokenize(text: str) -> set:
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    stopwords = {
        "the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "with",
        "must", "shall", "should", "be", "is", "are", "that", "this", "by",
        "from", "at", "as", "it", "if", "then", "when", "include", "includes",
        "analysis", "hazard"
    }
    return {w for w in words if w not in stopwords and len(w) > 2}


def completeness_check(test_case: Dict[str, Any]) -> Dict[str, Any]:
    missing_required = []
    empty_required = []

    for field in REQUIRED_FIELDS:
        if field not in test_case:
            missing_required.append(field)
        else:
            value = test_case[field]
            if value is None:
                empty_required.append(field)
            elif isinstance(value, str) and not value.strip():
                empty_required.append(field)

    optional_usefulness = {
        "has_steps": "steps" in test_case and bool(str(test_case.get("steps", "")).strip()),
        "has_notes": "notes" in test_case and bool(str(test_case.get("notes", "")).strip()),
    }

    is_complete = not missing_required and not empty_required

    return {
        "is_complete": is_complete,
        "missing_required_fields": missing_required,
        "empty_required_fields": empty_required,
        "optional_fields": optional_usefulness,
    }


def correctness_check(requirement_text: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
    requirement_tokens = tokenize(requirement_text)

    combined = " ".join([
        str(test_case.get("description", "")),
        str(test_case.get("input_data", "")),
        str(test_case.get("expected_output", "")),
        str(test_case.get("steps", "")),
        str(test_case.get("notes", "")),
    ])

    case_tokens = tokenize(combined)
    overlap = sorted(requirement_tokens.intersection(case_tokens))
    overlap_ratio = (len(overlap) / len(requirement_tokens)) if requirement_tokens else 0.0

    description_present = bool(str(test_case.get("description", "")).strip())
    expected_output_present = bool(str(test_case.get("expected_output", "")).strip())

    heuristic_match = description_present and expected_output_present and overlap_ratio >= 0.20

    return {
        "heuristic_match": heuristic_match,
        "requirement_keyword_overlap_ratio": round(overlap_ratio, 3),
        "overlapping_keywords": overlap[:20],
        "manual_review_note": (
            "Check whether the description truly tests the requirement, "
            "since automated correctness is only heuristic."
        ),
    }


def index_by_requirement(cases: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    indexed = {}
    for case in cases:
        requirement_id = str(case.get("requirement_id", "")).strip()
        indexed.setdefault(requirement_id, []).append(case)
    return indexed


def first_case_or_none(cases: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return cases[0] if cases else None


def main() -> None:
    requirements = load_json(INPUT_FILE)
    mistral_cases = load_json(MISTRAL_FILE)
    quant_cases = load_json(QUANT_FILE)

    mistral_index = index_by_requirement(mistral_cases)
    quant_index = index_by_requirement(quant_cases)

    per_requirement = []
    coverage_summary = {
        "total_requirements_checked": len(requirements),
        "both_models_produced_at_least_one_case": 0,
        "mistral_missing": [],
        "quantized_missing": [],
    }

    for req in requirements:
        requirement_id = req["requirement_id"]
        requirement_text = req["text"]

        mistral_req_cases = mistral_index.get(requirement_id, [])
        quant_req_cases = quant_index.get(requirement_id, [])

        mistral_has_case = len(mistral_req_cases) >= 1
        quant_has_case = len(quant_req_cases) >= 1

        if mistral_has_case and quant_has_case:
            coverage_summary["both_models_produced_at_least_one_case"] += 1
        if not mistral_has_case:
            coverage_summary["mistral_missing"].append(requirement_id)
        if not quant_has_case:
            coverage_summary["quantized_missing"].append(requirement_id)

        mistral_first = first_case_or_none(mistral_req_cases)
        quant_first = first_case_or_none(quant_req_cases)

        per_requirement.append({
            "requirement_id": requirement_id,
            "requirement_text": requirement_text,
            "coverage": {
                "mistral_has_case": mistral_has_case,
                "quantized_has_case": quant_has_case,
                "coverage_pass": mistral_has_case and quant_has_case,
            },
            "mistral_evaluation": {
                "completeness": completeness_check(mistral_first) if mistral_first else None,
                "correctness": correctness_check(requirement_text, mistral_first) if mistral_first else None,
                "test_case": mistral_first,
            },
            "quantized_evaluation": {
                "completeness": completeness_check(quant_first) if quant_first else None,
                "correctness": correctness_check(requirement_text, quant_first) if quant_first else None,
                "test_case": quant_first,
            },
        })

    summary = {
        "models_compared": {
            "mistral": "mistral-large-latest (Mistral API)",
            "quantized_mistral": "mistral:7b-instruct-q4_K_M (Ollama)",
        },
        "assignment_criteria": [
            "coverage",
            "correctness",
            "completeness",
        ],
        "coverage_summary": coverage_summary,
        "manual_review_required": True,
        "manual_review_note": (
            "Correctness cannot be fully guaranteed by automation alone. "
            "Use this report plus manual review of each generated test case."
        ),
        "per_requirement_results": per_requirement,
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()