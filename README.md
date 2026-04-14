# EffatGroup

COMP 5710 Group Project for group `EffatGroup`

## Group Members

- Joshua Chen
- Kyler Swindle
- Ayush Patel

## Overview

This project implements Verification & Validation for atomic rules extracted from `21 CFR 117.130` using Python scripts, JSON artifacts, and GitHub Actions.

## What This Project Does

1. Parses `inputs/21_CFR_117.130.md` into atomic CFR requirements.
2. Selects 10 atomic rules for the project scope.
3. Generates `requirements.json`.
4. Generates `expected_structure.json`.
5. Generates `test_cases.json`.
6. Verifies requirement and test-case completeness.
7. Validates requirement structure against expected parent-child mappings.
8. Runs the checks automatically in GitHub Actions.

## Repository Layout

```text
EffatGroup/
|-- .github/workflows/cfr-vv.yml
|-- inputs/
|   |-- 21_CFR_117.130.md
|   `-- README.md
|-- scripts/
|   |-- parse_cfr.py
|   |-- generate_expected_structure.py
|   |-- generate_test_cases.py
|   |-- verification.py
|   `-- validation.py
|-- requirements.json
|-- expected_structure.json
|-- test_cases.json
`-- README.md
```

## Selected Atomic Rules

The 10 selected rules are:

- `(a)(1)`
- `(a)(2)`
- `(b)(1)(i)`
- `(b)(1)(ii)`
- `(b)(1)(iii)`
- `(b)(2)(i)`
- `(b)(2)(ii)`
- `(b)(2)(iii)`
- `(c)(1)(i)`
- `(c)(1)(ii)`

## Quick Start

Run the project locally with:

```powershell
python scripts/parse_cfr.py
python scripts/generate_expected_structure.py
python scripts/generate_test_cases.py
python scripts/verification.py
python scripts/validation.py
```

## Current Status

The current local build has:

- generated `requirements.json`
- generated `expected_structure.json`
- generated `test_cases.json`
- passed `verification.py`
- passed `validation.py`

## Forensick Examples

Examples of forensic-style signals that can be shown in this project:

- Missing requirement
- Missing test case
- Invalid requirement ID
- Unexpected structure entry
- CI pass/fail evidence
