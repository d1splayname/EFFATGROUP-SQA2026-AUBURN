import json
import os
import re
from pathlib import Path
from typing import Any

from mistralai import Mistral
from ollama import Client as OllamaClient


ROOT = Path(__file__).resolve().parents[2]
INDIVIDUAL_DIR = ROOT / "individual"
INPUT_FILE = INDIVIDUAL_DIR / "input" / "selected_requirements_llm.json"
OUTPUT_DIR = INDIVIDUAL_DIR / "output"

MISTRAL_API_MODEL = "mistral-large-latest"
OLLAMA_MODEL = "mistral:7b-instruct-q4_K_M"


SYSTEM_PROMPT = """
You generate software test cases for regulatory requirements.

Return ONLY valid JSON.
Return a JSON array containing exactly one object.

Required fields:
- test_case_id
- requirement_id
- description
- input_data
- expected_output

Optional fields:
- steps
- notes

Rules:
- The test case must directly test the requirement text.
- The description must clearly explain what is being verified.
- input_data must describe the exact input or scenario.
- expected_output must clearly state the expected result.
- steps should be useful if included.
- notes should be useful if included.
- Do not include markdown code fences.
""".strip()


def load_requirements() -> list[dict[str, str]]:
    with INPUT_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("selected_requirements_llm.json must contain a JSON list.")

    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each requirement entry must be a JSON object.")
        if "requirement_id" not in item or "text" not in item:
            raise ValueError("Each requirement must contain 'requirement_id' and 'text'.")

    return data


def build_user_prompt(requirement: dict[str, str], test_case_id: str) -> str:
    return f"""
Requirement ID: {requirement['requirement_id']}
Requirement Text: {requirement['text']}
Required Test Case ID: {test_case_id}

Generate exactly one test case for this requirement.
Return a JSON array with one object only.
Make sure the object's test_case_id is exactly "{test_case_id}".
Make sure the object's requirement_id is exactly "{requirement['requirement_id']}".
""".strip()


def extract_json_payload(text: str) -> Any:
    text = text.strip()

    # Remove markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # First try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find first JSON array
    array_match = re.search(r"(\[\s*.*\s*\])", text, flags=re.DOTALL)
    if array_match:
        return json.loads(array_match.group(1))

    # Try to find first JSON object
    object_match = re.search(r"(\{\s*.*\s*\})", text, flags=re.DOTALL)
    if object_match:
        return json.loads(object_match.group(1))

    raise ValueError("Could not extract valid JSON from model output.")


def normalize_case(obj: dict[str, Any], test_case_id: str, requirement_id: str) -> dict[str, Any]:
    normalized = {
        "test_case_id": test_case_id,
        "requirement_id": requirement_id,
        "description": str(obj.get("description", "")).strip(),
        "input_data": obj.get("input_data", ""),
        "expected_output": obj.get("expected_output", ""),
    }

    if "steps" in obj:
        normalized["steps"] = obj["steps"]
    if "notes" in obj:
        normalized["notes"] = obj["notes"]

    return normalized


def parse_model_json(content: str, test_case_id: str, requirement_id: str) -> dict[str, Any]:
    parsed = extract_json_payload(content)

    if isinstance(parsed, dict):
        parsed = [parsed]

    if not isinstance(parsed, list) or len(parsed) != 1:
        raise ValueError("Model output must be a JSON array containing exactly one object.")

    obj = parsed[0]
    if not isinstance(obj, dict):
        raise ValueError("Model output array must contain a JSON object.")

    return normalize_case(obj, test_case_id, requirement_id)


def generate_with_mistral_api(requirement: dict[str, str], test_case_id: str) -> dict[str, Any]:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise EnvironmentError("MISTRAL_API_KEY is not set in the environment.")

    client = Mistral(api_key=api_key)

    response = client.chat.complete(
        model=MISTRAL_API_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(requirement, test_case_id)},
        ],
    )

    content = response.choices[0].message.content
    if isinstance(content, list):
        content = "".join(
            part.text if hasattr(part, "text") else str(part)
            for part in content
        )

    return parse_model_json(str(content), test_case_id, requirement["requirement_id"])


def generate_with_ollama(requirement: dict[str, str], test_case_id: str) -> dict[str, Any]:
    client = OllamaClient(host="http://localhost:11434")

    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(requirement, test_case_id)},
        ],
        options={"temperature": 0.2},
    )

    content = response["message"]["content"]
    return parse_model_json(content, test_case_id, requirement["requirement_id"])


def safe_generate(generator_name: str, generator_fn, requirement: dict[str, str], test_case_id: str) -> dict[str, Any]:
    try:
        return generator_fn(requirement, test_case_id)
    except Exception as exc:
        return {
            "test_case_id": test_case_id,
            "requirement_id": requirement["requirement_id"],
            "description": f"{generator_name} generation failed",
            "input_data": requirement["text"],
            "expected_output": "A valid JSON test case should have been generated.",
            "notes": f"Generation error: {exc}",
        }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    requirements = load_requirements()

    mistral_results = []
    quant_results = []

    for index, requirement in enumerate(requirements, start=1):
        test_case_id = f"TC-{index:03d}"

        mistral_case = safe_generate(
            "Mistral API",
            generate_with_mistral_api,
            requirement,
            test_case_id,
        )
        quant_case = safe_generate(
            "Ollama quantized Mistral",
            generate_with_ollama,
            requirement,
            test_case_id,
        )

        mistral_results.append(mistral_case)
        quant_results.append(quant_case)

    with (OUTPUT_DIR / "mistral_api_test_cases.json").open("w", encoding="utf-8") as f:
        json.dump(mistral_results, f, indent=2)

    with (OUTPUT_DIR / "mistral_quantized_test_cases.json").open("w", encoding="utf-8") as f:
        json.dump(quant_results, f, indent=2)

    print("Wrote:")
    print(f" - {OUTPUT_DIR / 'mistral_api_test_cases.json'}")
    print(f" - {OUTPUT_DIR / 'mistral_quantized_test_cases.json'}")


if __name__ == "__main__":
    main()