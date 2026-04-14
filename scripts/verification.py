import json
import re
import sys
from pathlib import Path


REQUIREMENT_ID_RE = re.compile(r"REQ-CFR-\d{3}[A-Z]+$")
PARENT_ID_RE = re.compile(r"REQ-CFR-\d{3}$")
TEST_CASE_ID_RE = re.compile(r"TC-\d{3}$")


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    requirements = load_json("requirements.json")
    test_cases = load_json("test_cases.json")

    if not requirements and not test_cases:
        print("Verification skipped: requirements.json and test_cases.json are empty.")
        sys.exit(0)

    failures: list[str] = []
    requirement_ids: set[str] = set()
    test_case_ids: set[str] = set()
    covered_requirement_ids: set[str] = set()

    for requirement in requirements:
        for field in ["requirement_id", "parent_requirement_id", "source_section", "description"]:
            if field not in requirement:
                failures.append(f"Requirement missing field '{field}': {requirement}")

        rid = requirement.get("requirement_id", "")
        parent_id = requirement.get("parent_requirement_id", "")
        description = requirement.get("description", "")
        source_section = requirement.get("source_section", "")

        if rid:
            if not REQUIREMENT_ID_RE.fullmatch(rid):
                failures.append(f"Invalid requirement_id format: {rid}")
            if rid in requirement_ids:
                failures.append(f"Duplicate requirement_id: {rid}")
            requirement_ids.add(rid)

        if parent_id and not PARENT_ID_RE.fullmatch(parent_id):
            failures.append(f"Invalid parent_requirement_id format: {parent_id}")

        if rid and parent_id and not rid.startswith(parent_id):
            failures.append(f"Parent-child mismatch: {rid} does not start with {parent_id}")

        if not str(description).strip():
            failures.append(f"Empty description for requirement: {rid}")

        if not str(source_section).strip():
            failures.append(f"Empty source_section for requirement: {rid}")

    for test_case in test_cases:
        for field in ["test_case_id", "requirement_id", "description", "input_data", "expected_output"]:
            if field not in test_case:
                failures.append(f"Test case missing field '{field}': {test_case}")

        test_case_id = test_case.get("test_case_id", "")
        requirement_id = test_case.get("requirement_id", "")

        if test_case_id:
            if not TEST_CASE_ID_RE.fullmatch(test_case_id):
                failures.append(f"Invalid test_case_id format: {test_case_id}")
            if test_case_id in test_case_ids:
                failures.append(f"Duplicate test_case_id: {test_case_id}")
            test_case_ids.add(test_case_id)

        if requirement_id:
            covered_requirement_ids.add(requirement_id)
            if requirement_ids and requirement_id not in requirement_ids:
                failures.append(f"Test case references unknown requirement_id: {requirement_id}")

    for rid in sorted(requirement_ids):
        if rid not in covered_requirement_ids:
            failures.append(f"No test case found for requirement: {rid}")

    if failures:
        print("Verification FAILED:")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)

    print("Verification passed: requirements and test cases are structurally complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()

