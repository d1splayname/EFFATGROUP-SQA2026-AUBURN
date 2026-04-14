import argparse
import json
from collections import OrderedDict
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Generate expected_structure.json from requirements.json.")
    parser.add_argument("--requirements", default="requirements.json", help="Input requirements JSON file.")
    parser.add_argument("--output", default="expected_structure.json", help="Output expected structure file.")
    return parser.parse_args()


def main():
    args = parse_args()
    requirements_path = Path(args.requirements)
    output_path = Path(args.output)

    requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
    expected_structure: OrderedDict[str, list[str]] = OrderedDict()

    for requirement in requirements:
        parent_id = requirement["parent_requirement_id"]
        requirement_id = requirement["requirement_id"]
        child_suffix = requirement_id[len(parent_id) :]

        if parent_id not in expected_structure:
            expected_structure[parent_id] = []
        expected_structure[parent_id].append(child_suffix)

    output_path.write_text(json.dumps(expected_structure, indent=2), encoding="utf-8")
    print(f"Wrote expected structure for {len(expected_structure)} parent requirements to {output_path}.")


if __name__ == "__main__":
    main()

