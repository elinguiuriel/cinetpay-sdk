"""Repository-level acceptance harness for the CinetPay SDK.

The harness turns documented repository expectations into executable scenarios.
Unlike unit tests that target isolated implementation details, the harness asks
whether the SDK still behaves according to the contract encoded in the
repository's scenario fixtures.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .client import CinetPayClient, SANDBOX_BASE_URL
from .transport import HttpResponse


def _default_scenario_dir() -> Path:
    """Return the default directory containing repository harness scenarios."""
    return Path(__file__).resolve().parents[2] / "harness" / "scenarios"


@dataclass(frozen=True)
class ScenarioResult:
    """Result of executing one repository harness scenario."""

    name: str
    passed: bool
    message: str


class ScenarioTransport:
    """Deterministic transport used by harness scenarios.

    Each scenario provides a fixed sequence of canned HTTP responses. This
    transport records the outgoing requests so the harness can assert both the
    returned models and the shape of the HTTP conversation.
    """

    def __init__(self, responses: Iterable[Mapping[str, Any]]) -> None:
        """Create a transport from a list of scenario response definitions."""
        self._responses = [
            HttpResponse(
                status_code=int(response["status_code"]),
                json_body=dict(response.get("json_body", {})),
                headers=dict(response.get("headers", {})),
            )
            for response in responses
        ]
        self.calls: List[Dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> HttpResponse:
        """Return the next canned response and record the outgoing call."""
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers or {}),
                "json_data": json_data,
                "timeout": timeout,
            }
        )
        if not self._responses:
            raise AssertionError("Harness transport ran out of responses")
        return self._responses.pop(0)

    def close(self) -> None:
        """Satisfy the transport protocol without doing anything."""
        return None


def load_scenarios(directory: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load all JSON scenario definitions from a directory."""
    scenario_dir = directory or _default_scenario_dir()
    if not scenario_dir.exists():
        raise FileNotFoundError(f"Scenario directory not found: {scenario_dir}")
    scenarios = []
    for path in sorted(scenario_dir.glob("*.json")):
        scenarios.append(json.loads(path.read_text(encoding="utf-8")))
    return scenarios


def _read_path(value: Any, path: str) -> Any:
    """Resolve a dotted attribute-or-dictionary path from a result object."""
    current = value
    for part in path.split("."):
        if isinstance(current, Mapping):
            current = current[part]
        else:
            current = getattr(current, part)
    return current


def _dispatch(client: CinetPayClient, operation: Mapping[str, Any]) -> Any:
    """Dispatch a scenario operation to the matching client method."""
    name = operation["name"]
    if name == "create_payment":
        return client.create_payment(operation["payload"])
    if name == "get_payment_status":
        return client.get_payment_status(operation["identifier"])
    if name == "create_transfer":
        return client.create_transfer(operation["payload"])
    if name == "get_transfer_status":
        return client.get_transfer_status(operation["transaction_id"])
    if name == "get_balances":
        return client.get_balances()
    raise ValueError(f"Unsupported harness operation: {name}")


def _assert_expectations(
    *,
    result: Any,
    transport: ScenarioTransport,
    expect: Mapping[str, Any],
) -> None:
    """Assert both model-level expectations and the HTTP call sequence."""
    for attr_path, expected in expect.get("attrs", {}).items():
        actual = _read_path(result, attr_path)
        if actual != expected:
            raise AssertionError(
                f"Expected {attr_path}={expected!r}, got {actual!r}"
            )

    call_sequence = expect.get("call_sequence", [])
    if len(transport.calls) != len(call_sequence):
        raise AssertionError(
            f"Expected {len(call_sequence)} HTTP calls, got {len(transport.calls)}"
        )

    for index, expected_call in enumerate(call_sequence):
        actual_call = transport.calls[index]
        expected_url = f"{SANDBOX_BASE_URL}{expected_call['path']}"
        if actual_call["method"] != expected_call["method"]:
            raise AssertionError(
                f"Call {index} expected method {expected_call['method']}, got {actual_call['method']}"
            )
        if actual_call["url"] != expected_url:
            raise AssertionError(
                f"Call {index} expected URL {expected_url}, got {actual_call['url']}"
            )
        expected_auth = expected_call.get("authorization")
        actual_auth = actual_call["headers"].get("Authorization")
        if expected_auth != actual_auth:
            raise AssertionError(
                f"Call {index} expected Authorization {expected_auth!r}, got {actual_auth!r}"
            )


def run_scenario(definition: Mapping[str, Any]) -> ScenarioResult:
    """Execute one harness scenario and capture its pass/fail result."""
    transport = ScenarioTransport(definition["responses"])
    client = CinetPayClient("key", "password", transport=transport)
    try:
        result = _dispatch(client, definition["operation"])
        _assert_expectations(result=result, transport=transport, expect=definition["expect"])
    except Exception as exc:
        return ScenarioResult(name=definition["name"], passed=False, message=str(exc))
    return ScenarioResult(name=definition["name"], passed=True, message="ok")


def run_repository_harness(directory: Optional[Path] = None) -> List[ScenarioResult]:
    """Execute every harness scenario found in the given directory."""
    return [run_scenario(definition) for definition in load_scenarios(directory)]


def main() -> int:
    """Run the repository harness as a small CLI entry point."""
    results = run_repository_harness()
    failed = [result for result in results if not result.passed]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.message}")
    return 1 if failed else 0
