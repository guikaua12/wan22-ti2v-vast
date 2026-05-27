import asyncio
import importlib
import json
import sys
import threading
import types


class JsonRequest:
    def __init__(self, body):
        self.body = body

    async def json(self):
        return self.body


def response_json(response):
    return json.loads(response.text)


def test_drain_controller_starts_executor_once():
    from executor.server import DrainController

    started = threading.Event()
    release = threading.Event()

    def runner():
        started.set()
        release.wait(timeout=1)

    controller = DrainController(runner=runner)

    first = asyncio.run(controller.drain(JsonRequest({"kind": "drain_queue"})))
    assert first.status == 202
    assert response_json(first) == {"ok": True, "started": True, "running": True}
    assert started.wait(timeout=1)

    second = asyncio.run(controller.drain(JsonRequest({"kind": "drain_queue"})))
    assert second.status == 202
    assert response_json(second) == {"ok": True, "started": False, "running": True}

    release.set()
    assert controller.wait(timeout=1)


def test_drain_controller_rejects_unknown_payload():
    from executor.server import DrainController

    calls = []
    controller = DrainController(runner=lambda: calls.append("run"))

    response = asyncio.run(controller.drain(JsonRequest({"kind": "generate"})))

    assert response.status == 400
    assert response_json(response) == {"error": "unsupported payload"}
    assert calls == []


def test_executor_module_imports_as_package(monkeypatch):
    fake_boto3 = types.ModuleType("boto3")
    fake_boto3.client = lambda *args, **kwargs: object()
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    module = importlib.import_module("executor.executor")

    assert callable(module.run)
