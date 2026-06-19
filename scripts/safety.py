#!/usr/bin/env python3
"""Reference client for the Gecko token-safety oracle — zero dependencies.

Readable, copy-paste-able example of how to gate a Solana token from any Python
runtime (no `requests`/`httpx` needed — stdlib only). Prints the verdict and
exits non-zero on `block` so it composes in scripts/CI.

Usage:
    python scripts/safety.py <SPL_MINT>
    python scripts/safety.py JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN

Exit codes: 0 = ok | 10 = caution | 20 = block | 30 = unknown
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://api.geckovision.tech/safety"
TIMEOUT_S = 8.0
_EXIT = {"ok": 0, "caution": 10, "block": 20, "unknown": 30}


def check(mint: str) -> dict:
    """POST a mint, return the verdict dict. Fail-OPEN to gate=unknown on error."""
    body = json.dumps({"mint": mint}).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310 (trusted host)
            return json.load(resp)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return {"gate": "unknown", "reasons": ["safety check could not run"]}


def _reasons(v: dict) -> list[str]:
    out: list[str] = []
    for block in (v.get("information_mev"), v.get("wash_risk")):
        if isinstance(block, dict):
            out += block.get("reasons") or []
    return out or (v.get("rug_flags") or [])


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python scripts/safety.py <SPL_MINT>", file=sys.stderr)
        return 2
    v = check(argv[1])
    gate = v.get("gate", "unknown")
    icon = {"ok": "✅", "caution": "⚠️", "block": "❌", "unknown": "❓"}.get(gate, "❓")
    print(f"{icon}  gate = {gate.upper()}  ({argv[1]})")
    for r in _reasons(v)[:4]:
        print(f"    - {r}")
    if gate in ("block", "caution", "unknown"):
        print("    note: 'unknown' is NOT safe (the check could not run).", file=sys.stderr) if gate == "unknown" else None
    return _EXIT.get(gate, 30)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
