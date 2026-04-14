import argparse
import json
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Generate minimal test cases for selected CFR requirements.")
    parser.add_argument("--requirements", default="requirements.json", help="Input requirements JSON file.")
    parser.add_argument("--structure", default="expected_structure.json", help="Input expected structure JSON file.")
    parser.add_argument("--output", default="test_cases.json", help="Output test case JSON file.")
    return parser.parse_args()


def build_selected_requirement_ids(expected_structure: dict[str, list[str]]) -> set[str]:
    selected_ids = set()
    for parent_id, suffixes in expected_structure.items():
        for suffix in suffixes:
            selected_ids.add(f"{parent_id}{suffix}")
    return selected_ids


def build_test_case(index: int, requirement: dict) -> dict:
    rid = requirement["requirement_id"]
    description = requirement["description"]
    source_section = requirement["source_section"]
    test_case_id = f"TC-{index:03d}"

    return {
        "test_case_id": test_case_id,
        "requirement_id": rid,
        "description": f"Verify that the evidence satisfies requirement {rid}: {description}",
        "input_data": {
            "source_section": source_section,
            "evidence": f"Provide a record, observation, or document that demonstrates: {description}"
        },
        "expected_output": {
            "status": "pass",
            "message": f"Requirement {rid} is satisfied when the submitted evidence demonstrates: {description}"
        },
        "steps": [
            f"Review the evidence mapped to {source_section}.",
            "Compare the evidence against the atomic requirement description.",
            "Mark the test as pass only if the evidence fully satisfies the requirement."
        ],
        "notes": "This is a minimal generated test case template and may be refined manually."
    }


def main():
    args = parse_args()
    requirements = json.loads(Path(args.requirements).read_text(encoding="utf-8"))
    expected_structure = json.loads(Path(args.structure).read_text(encoding="utf-8"))

    selected_ids = build_selected_requirement_ids(expected_structure)
    filtered_requirements = [
        requirement for requirement in requirements if requirement["requirement_id"] in selected_ids
    ]

    if not expected_structure:
        filtered_requirements = requirements

    test_cases = [build_test_case(index, requirement) for index, requirement in enumerate(filtered_requirements, start=1)]
    Path(args.output).write_text(json.dumps(test_cases, indent=2), encoding="utf-8")
    print(f"Wrote {len(test_cases)} test cases to {args.output}.")


if __name__ == "__main__":
    main()

