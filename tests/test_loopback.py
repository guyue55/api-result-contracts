"""在随机本机端口验证真实HTTP同步／异步消费者和错误，不使用外部服务。"""

import asyncio
import socket
import threading
import time
from contextlib import contextmanager

import httpx
import pytest
import uvicorn

from api_result_contracts import RemoteError
from api_result_contracts.integrations.httpx import arequest_json, request_json
from examples.fastapi_app import Item, app, registry


@contextmanager
def server():
    # 由当前进程持有端口到交给服务端，不释放后重新抢占。
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    service = uvicorn.Server(uvicorn.Config(app, log_level="critical", lifespan="off"))
    thread = threading.Thread(target=service.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not service.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert service.started
        yield f"http://127.0.0.1:{port}"
    finally:
        service.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive()


def test_real_http_sync_async_validation_and_errors():
    with server() as base:
        with httpx.Client(base_url=base, trust_env=False, timeout=5) as client:
            result = request_json(
                client, "POST", "/api/v2/echo", Item, registry=registry, json={"quantity": 12}
            )
            assert result.data.quantity == 12 and result.code == 0 and result.meta.trace_id
            with pytest.raises(RemoteError) as raised:
                request_json(client, "GET", "/api/v2/conflict", Item, registry=registry)
            assert raised.value.code == 409001
            response = client.post("/api/v2/echo", json={"quantity": "invalid"})
            assert response.status_code in {400, 422}
            assert response.json()["code"] > 0

        async def parallel():
            async with httpx.AsyncClient(base_url=base, trust_env=False, timeout=5) as client:
                values = await asyncio.gather(
                    *(
                        arequest_json(
                            client,
                            "POST",
                            "/api/v2/echo",
                            Item,
                            registry=registry,
                            json={"quantity": n},
                        )
                        for n in range(8)
                    )
                )
                assert [v.data.quantity for v in values] == list(range(8))
                assert len({v.meta.trace_id for v in values}) == 8

        asyncio.run(parallel())
