# Architecture

This repository follows a harness-first layout inspired by OpenAI's "Harness engineering" approach:

- repository knowledge is explicit and versioned
- behavior is validated through executable scenarios
- architecture is enforced with mechanical checks
- local scripts provide short, repeatable feedback loops

## Module Layers

The SDK has a narrow layered structure:

1. `exceptions.py`
2. `models.py`
3. `transport.py`
4. `client.py`
5. `harness.py`
6. `__init__.py`

Dependency rules:

- `exceptions.py` imports no local SDK modules
- `models.py` imports no local SDK modules
- `transport.py` may import `exceptions.py`
- `client.py` may import `exceptions.py`, `models.py`, `transport.py`
- `harness.py` may import `client.py` and `transport.py`
- `__init__.py` only re-exports public symbols

These rules are enforced by `tests/test_architecture.py`.

## Documentation Standard

This repository treats code documentation as a mechanical quality property, not a best-effort convention.

- every public module must explain its role
- every public class must describe its responsibility
- every public method and property must explain behavior, especially where it encodes an external CinetPay rule
- internal helpers should be documented when the transformation or control flow is not obvious

These expectations are enforced by `tests/test_documentation.py`.

## Behavioral Source Of Truth

Behavioral expectations are encoded in three places:

- `docs/cinetpay-sandbox-contract.md`: distilled external API contract
- `harness/scenarios/*.json`: executable acceptance scenarios
- unit tests: implementation-focused checks

When the external API is updated:

1. update the contract doc
2. add or update harness scenarios
3. adapt implementation

## Harness Design

The repository harness lives in `src/cinetpay_sdk/harness.py`.

It:

- loads scenario fixtures from `harness/scenarios/`
- drives the SDK through a fake transport
- asserts response behavior and HTTP call patterns
- produces a single pass/fail report suitable for CI

The harness is intended to answer "does the repository still implement the documented SDK contract?".

## Quality Loop

The default quality loop is:

1. bytecode compile check
2. unit and architecture tests
3. repository harness

This is executed by `python scripts/run_quality.py`.
