import json
import re
import sys
from pathlib import Path


PARENT_ID_RE = re.compile(r"REQ-CFR-\d{3}$")
SUFFIX_RE = re.compile(r"[A-Z]+$")


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    requirements = load_json("requirements.json")
    expected_structure = load_json("expected_structure.json")

    if not requirements and not expected_structure:
        print("Validation skipped: requirements.json and expected_structure.json are empty.")
        sys.exit(0)

    actual_ids = {requirement["requirement_id"] for requirement in requirements}
    failures: list[str] = []

    if requirements and not expected_structure:
        failures.append("expected_structure.json is empty while requirements.json contains requirements.")

    for parent_id, suffixes in expected_structure.items():
        if not PARENT_ID_RE.fullmatch(parent_id):
            failures.append(f"Invalid parent ID in expected_structure.json: {parent_id}")

        if not isinstance(suffixes, list) or not suffixes:
            failures.append(f"Parent {parent_id} must map to a non-empty list of child letters.")
            continue

        for suffix in suffixes:
            if not SUFFIX_RE.fullmatch(suffix):
                failures.append(f"Invalid child suffix '{suffix}' under parent {parent_id}")
                continue

            requirement_id = f"{parent_id}{suffix}"
            if requirement_id not in actual_ids:
                failures.append(f"Missing requirement from expected structure: {requirement_id}")

    for requirement_id in actual_ids:
        matched_parent = next((parent for parent in expected_structure if requirement_id.startswith(parent)), None)
        if not matched_parent:
            failures.append(f"Requirement not mapped by expected_structure.json: {requirement_id}")
            continue
        if matched_parent:
            suffix = requirement_id[len(matched_parent) :]
            if suffix not in expected_structure[matched_parent]:
                failures.append(f"Unexpected requirement not listed in expected_structure.json: {requirement_id}")

    if failures:
        print("Validation FAILED:")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)

    print("Validation passed: requirements.json matches expected_structure.json.")
    sys.exit(0)


if __name__ == "__main__":
    main()
