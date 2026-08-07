"""Prove the server answers a real MCP handshake and a real tool call over stdio."""

import json
import subprocess
import sys
from pathlib import Path


def _exchange(process, message):
    """Send one JSON-RPC message and read the next line the server writes back."""
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()
    return json.loads(process.stdout.readline())


def _main():
    """Run initialize, tools/list, and one tools/call against a live server process."""
    server = Path(__file__).with_name("mcp_server.py")
    arguments = [sys.executable, str(server)]
    process = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    handshake = _exchange(
        process,
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"capabilities": {}}},
    )
    assert handshake["result"]["serverInfo"]["name"] == "overengineered-mcp", handshake
    listing = _exchange(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = sorted(tool["name"] for tool in listing["result"]["tools"])
    assert names == ["echo", "slugify", "statistics", "sum_numbers", "word_count"], names
    call = {"name": "sum_numbers", "arguments": {"numbers": [1, 2, 3.5]}}
    called = _exchange(
        process, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": call}
    )
    assert called["result"]["content"][0]["text"] == "6.5", called
    process.stdin.close()
    process.wait(timeout=10)
    sys.stdout.write(f"smoke ok: handshake, {len(names)} tools listed, sum_numbers returned 6.5\n")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
