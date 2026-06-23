"""Zendesk source connector (pull).

Phase 2 target. Fetches tickets from Zendesk and maps them to canonical signals
via a user-defined field map (reuse Elvis's api_poll design,
reference/elvis/supabase/functions/sync-source/index.ts:79-160).

TODO(Phase 2):
  - OAuth2 / API token auth from connector config
  - incremental pull using last_synced_at / cursor
  - map fields: text, tags, external_id, recorded_at, customer_id, account_id
  - dedupe by external_id
"""

from __future__ import annotations

from typing import Any


class ZendeskSourceConnector:
    connector_type = "zendesk"

    def pull(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError("Phase 2: implement Zendesk ticket pull + field mapping")
