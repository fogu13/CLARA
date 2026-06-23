"""Slack destination connector (push).

Phase 2 target. Implements the `notify` action type as a real chat.postMessage
call. Replaces Elvis's simulated notify (reference/elvis/supabase/functions/
evaluate-rules/index.ts:142-153, returned {delivered: true} without calling).

TODO(Phase 2):
  - bot token / incoming webhook from connector config
  - build message from insight summary + action context
  - return {external_id: <channel/ts>, status, raw}
"""

from __future__ import annotations

from typing import Any


class SlackDestinationConnector:
    connector_type = "slack"

    def push(self, action: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Phase 2: implement Slack chat.postMessage")
