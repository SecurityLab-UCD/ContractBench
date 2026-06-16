from __future__ import annotations

import asyncio

import httpx

from benchmark.environments.web_ephemeral.app import WebEphemeralConfig, create_app
from benchmark.environments.web_ephemeral.eval import _DownloadListParser


def test_task_multi_route_renders_download_list():
    async def _run() -> None:
        app = create_app(WebEphemeralConfig(base_url="http://testserver", secret_key=b"tga-dev-secret"))
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get("/task/multi", params={"ttls": "5,2,5", "payload_bytes": 64, "trap": "plain"})
            assert resp.status_code == 200

            parser = _DownloadListParser()
            parser.feed(resp.text)
            assert len(parser.items) == 3
            assert all(item.href for item in parser.items)

    asyncio.run(_run())
