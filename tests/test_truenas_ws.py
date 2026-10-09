"""Exercise the TrueNAS JSON-RPC client against a fake local websocket server."""
import json

import pytest
import websockets

from app import demo
from app.integrations import truenas

RESULTS = {
    "system.info": demo.TN_INFO,
    "pool.query": demo.TN_POOLS,
    "pool.dataset.query": demo.TN_DATASETS,
    "alert.list": demo.TN_ALERTS,
    "app.query": demo.TN_APPS,
}


async def _handler(ws):
    authed = False
    async for raw in ws:
        msg = json.loads(raw)
        # Unsolicited notification first, to make sure the client skips it.
        await ws.send(json.dumps({"jsonrpc": "2.0", "method": "collection_update", "params": {}}))
        if msg["method"] == "auth.login_with_api_key":
            authed = msg["params"] == ["good-key"]
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": authed}))
        elif not authed:
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": 13, "message": "Not authenticated"}}))
        elif msg["method"] in RESULTS:
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": RESULTS[msg["method"]]}))
        else:  # e.g. replication.query unavailable
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": "Method not found"}}))


@pytest.fixture
async def server():
    async with websockets.serve(_handler, "127.0.0.1", 0) as srv:
        yield srv.sockets[0].getsockname()[1]


async def test_fetch_over_websocket(server):
    d = await truenas.fetch({"url": f"http://127.0.0.1:{server}", "api_key": "good-key"})
    assert d["hostname"] == "truenas"
    assert [p["name"] for p in d["pools"]] == ["tank", "fast"]
    assert d["apps"][0]["url"].startswith("http://127.0.0.1:")
    assert d["replications"] == []  # optional method failure tolerated


async def test_bad_key(server):
    with pytest.raises(RuntimeError, match="rejected"):
        await truenas.fetch({"url": f"http://127.0.0.1:{server}", "api_key": "nope"})
