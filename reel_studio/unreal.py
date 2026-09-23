"""Minimal UnrealClaude HTTP adapter.

The adapter intentionally uses the documented localhost seam so the production
controller is not coupled to one MCP client. Unreal must already be running.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any


class UnrealClaude:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url.rstrip("/")

    def status(self) -> dict[str, Any]:
        req = urllib.request.Request(f"{self.base_url}/mcp/status", method="GET")
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def tool(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps(args or {}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/mcp/tool/{name}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
