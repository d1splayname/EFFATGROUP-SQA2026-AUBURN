import argparse
import json
import re
from collections import OrderedDict, defaultdict
from pathlib import Path


CLAUSE_RE = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\((?P<paren>[A-Za-z0-9IVXLCMivxlcm]+)\)|(?P<dot>[A-Za-z0-9IVXLCMivxlcm]+)\.)(?:\s+(?P<text>.+?))?\s*$"
)
HEADING_RE = re.compile(r"^\s*(?P<hashes>#+)\s+(?P<body>.+?)\s*$")
SECTION_RE = re.compile(r"(\d+\s+CFR\s+\d+\.\d+)", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")


def parse_args():
    parser = argparse.ArgumentParser(description="Parse CFR markdown into atomic requirements.")
    parser.add_argument(
        "--input",
        default="inputs/21_CFR_117.130.md",
        help="Input markdown file containing the CFR section.",
    )
    parser.add_argument(
        "--output",
        default="requirements.json",
        help="Output JSON file for selected atomic requirements.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of atomic rules to keep from the parsed list.",
    )
    return parser.parse_args()


def infer_section_label(input_path: Path) -> str:
    match = SECTION_RE.search(input_path.stem.replace("_", " "))
    if match:
        return match.group(1).upper()
    return input_path.stem.replace("_", " ")


def is_roman(token: str) -> bool:
    return bool(re.fullmatch(r"[ivxlcdm]+", token.lower()))


def classify_rank(token: str, stack: list[dict]) -> int:
    cleaned = token.strip().strip("().")
    if cleaned.isdigit():
        return 2
    if cleaned.isalpha():
        if cleaned.isupper():
            return 4
        lower = cleaned.lower()
        if len(lower) == 1:
            if stack and stack[-1]["rank"] == 2 and lower in "ivxlcdm":
                return 3
            return 1
        if is_roman(lower):
            return 3
        return 1
    return 5


def normalize_text(text: str) -> str:
    text = MARKDOWN_LINK_RE.sub(r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[*_#>]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -;:")


def append_continuation(node: dict, text: str) -> None:
    if not text.strip():
        return
    extra = normalize_text(text)
    if extra:
        node["text"] = f"{node['text']} {extra}".strip()


def parse_markdown(input_path: Path) -> tuple[str, list[dict]]:
    section_label = infer_section_label(input_path)
    roots: list[dict] = []
    stack: list[dict] = []

    for raw_line in input_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        heading_match = HEADING_RE.match(line)
        candidate = heading_match.group("body") if heading_match else line
        match = CLAUSE_RE.match(candidate)
        if match:
            token = match.group("paren") or match.group("dot")
            text = normalize_text(match.group("text") or "")
            rank = classify_rank(token, stack)

            while stack and stack[-1]["rank"] >= rank:
                stack.pop()

            path_tokens = [item["token"] for item in stack] + [token]
            source_section = section_label + "".join(f"({value})" for value in path_tokens)

            node = {
                "token": token,
                "rank": rank,
                "text": text,
                "children": [],
                "source_section": source_section,
            }

            if stack:
                stack[-1]["children"].append(node)
            else:
                roots.append(node)

            stack.append(node)
            continue

        if heading_match:
            continue

        if stack:
            append_continuation(stack[-1], line)

    return section_label, roots


def collect_atomic_nodes(nodes: list[dict], path: list[dict] | None = None) -> list[dict]:
    path = path or []
    atomic: list[dict] = []

    for node in nodes:
        current_path = path + [node]
        if node["children"]:
            atomic.extend(collect_atomic_nodes(node["children"], current_path))
            continue

        top = current_path[0]
        context_parts = [normalize_text(item["text"]) for item in current_path if normalize_text(item["text"])]
        atomic.append(
            {
                "description": " ".join(context_parts),
                "source_section": node["source_section"],
                "top_level_section": top["source_section"],
            }
        )

    return atomic


def number_to_letters(index: int) -> str:
    letters = []
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def build_requirements(atomic_rules: list[dict], limit: int, input_name: str) -> list[dict]:
    selected = atomic_rules[:limit]
    parent_ids: OrderedDict[str, str] = OrderedDict()
    child_counts: defaultdict[str, int] = defaultdict(int)
    requirements: list[dict] = []

    for atomic in selected:
        top_level_section = atomic["top_level_section"]
        if top_level_section not in parent_ids:
            parent_ids[top_level_section] = f"REQ-CFR-{len(parent_ids) + 1:03d}"

        parent_id = parent_ids[top_level_section]
        child_counts[parent_id] += 1
        child_letter = number_to_letters(child_counts[parent_id])

        requirements.append(
            {
                "requirement_id": f"{parent_id}{child_letter}",
                "parent_requirement_id": parent_id,
                "source_section": atomic["source_section"],
                "top_level_section": top_level_section,
                "description": atomic["description"],
                "source_file": input_name,
            }
        )

    return requirements


def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}. Add the assignment markdown before running the parser."
        )

    _, roots = parse_markdown(input_path)
    atomic_rules = collect_atomic_nodes(roots)
    requirements = build_requirements(atomic_rules, args.limit, input_path.name)

    output_path.write_text(json.dumps(requirements, indent=2), encoding="utf-8")
    print(
        f"Parsed {len(atomic_rules)} atomic rules and wrote {len(requirements)} selected requirements to {output_path}."
    )


if __name__ == "__main__":
    main()
