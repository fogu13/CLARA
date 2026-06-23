"""Jira destination connector (push).

Phase 2 target. Replaces Odradek_2's local-only JiraIssueDraft
(apps/api/app/services/workflow.py:125-142, hardcoded project_key="ODR")
with a real POST /rest/api/3/issue call, behind the governance approval gate.

TODO(Phase 2):
  - API token / OAuth from connector config
  - build issue payload from action + problem evidence
  - return {external_id: <Jira key>, status, raw}
  - surface create failures as non-fatal action_log entries
"""

from __future__ import annotations

from typing import Any


class JiraDestinationConnector:
    connector_type = "jira"

    def push(self, action: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Phase 2: implement Jira issue creation via REST API")
