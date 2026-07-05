"""Test the compliance add-on without a live LLM — mock the HTTP call, assert the
prompt carries the regulatory knowledge base and the tool response round-trips.

Run:  cd add-ons/compliance-checker && python -m pytest test_compliance.py
"""

from __future__ import annotations

import json

import pytest

import compliance
from compliance import ASSESSMENT_TOOL, SYSTEM_PROMPT, ComplianceError, assess_compliance


def test_prompt_and_schema_are_intact() -> None:
    # The knowledge base is the IP — guard the key regs and the required output fields.
    assert "Regulation 2024/1689" in SYSTEM_PROMPT  # EU AI Act
    assert "2016/679" in SYSTEM_PROMPT  # GDPR
    assert "PROHIBITED AI PRACTICES" in SYSTEM_PROMPT
    assert "Digital Omnibus" in SYSTEM_PROMPT
    required = ASSESSMENT_TOOL["function"]["parameters"]["required"]
    assert {"overall_score", "gdpr_score", "eu_ai_act_score", "prohibited_practices_detected"} <= set(required)


def test_assess_parses_tool_call(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "overall_score": 72,
        "risk_level": "medium",
        "summary": "Largely compliant.",
        "gdpr_score": 70,
        "eu_ai_act_score": 74,
        "findings": [],
        "required_actions": [],
        "compliant_aspects": ["opt-in consent captured"],
        "prohibited_practices_detected": [],
    }

    class _Resp:
        status_code = 200

        def json(self) -> dict:
            return {"choices": [{"message": {"tool_calls": [
                {"function": {"name": "submit_compliance_assessment", "arguments": json.dumps(payload)}}
            ]}}]}

    class _Client:
        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *a):  # noqa: ANN002
            return False

        def post(self, *a, **k):  # noqa: ANN002, ANN003
            return _Resp()

    monkeypatch.setattr(compliance.httpx, "Client", lambda *a, **k: _Client())
    result = assess_compliance(title="Spring promo", campaign_description="Email blast to all users.")
    assert result["overall_score"] == 72
    assert result["risk_level"] == "medium"


def test_no_tool_call_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        status_code = 200

        def json(self) -> dict:
            return {"choices": [{"message": {"tool_calls": []}}]}

    class _Client:
        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *a):  # noqa: ANN002
            return False

        def post(self, *a, **k):  # noqa: ANN002, ANN003
            return _Resp()

    monkeypatch.setattr(compliance.httpx, "Client", lambda *a, **k: _Client())
    with pytest.raises(ComplianceError):
        assess_compliance(title="x", campaign_description="y")
