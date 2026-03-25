# AGENTS.md

This repository is optimized for agent-readable maintenance.

## Mission

Maintain a small, reliable Python SDK for the CinetPay sandbox API with:

- explicit repository contracts
- executable acceptance harnesses
- mechanical architectural checks
- short feedback loops

## Source Of Truth

When behavior is ambiguous, prefer these files over ad hoc assumptions:

1. `docs/cinetpay-sandbox-contract.md`
2. `docs/architecture.md`
3. `harness/scenarios/*.json`
4. `README.md`

If a change affects runtime behavior, update the contract and the matching harness scenario in the same change.

## Package Boundaries

- `src/cinetpay_sdk/models.py`: request/response models and local validation only
- `src/cinetpay_sdk/transport.py`: HTTP transport only
- `src/cinetpay_sdk/client.py`: orchestration, auth lifecycle, API error handling
- `src/cinetpay_sdk/exceptions.py`: exception hierarchy only
- `src/cinetpay_sdk/harness.py`: repository evaluation harness
- `src/cinetpay_sdk/__init__.py`: public exports only

## Invariants

- Keep the public API small and explicit.
- Put new behavioral rules in docs and harness scenarios, not just in prose comments.
- Prefer boring, inspectable stdlib-based code over opaque abstractions.
- Do not hide CinetPay assumptions in test bodies if they can live in the contract docs or scenario fixtures.
- When adding an endpoint, add at least one harness scenario that exercises the expected success path.
- If a bug fix changes control flow, add or update a harness scenario before considering the task complete.

## Feedback Loop

Repository commands:

- `python scripts/run_harness.py`
- `python scripts/run_quality.py`
- `python -m unittest discover -s tests -v`

`run_quality.py` is the default gate. It compiles the code, runs the tests, and executes the repository harness.

## Change Protocol

For any non-trivial SDK change:

1. Update the contract in `docs/cinetpay-sandbox-contract.md` if behavior changed or was clarified.
2. Add or update a scenario in `harness/scenarios/`.
3. Implement the code change.
4. Run `python scripts/run_quality.py`.

## Design Bias

What the agent cannot see does not exist. Encode decisions in the repository.
