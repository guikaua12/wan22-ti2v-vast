import threading
from collections.abc import Callable

from aiohttp import web

from executor.config import load_config


def default_runner() -> None:
    from executor.executor import run

    run()


class DrainController:
    def __init__(self, runner: Callable[[], None] = default_runner):
        self._runner = runner
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._last_error: str | None = None

    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def wait(self, timeout: float | None = None) -> bool:
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout=timeout)
        return not thread.is_alive()

    async def health(self, _request):
        return web.json_response({
            "ok": True,
            "running": self.running(),
            "lastError": self._last_error,
        })

    async def drain(self, request):
        body = await request.json()
        if body.get("kind") != "drain_queue":
            return web.json_response({"error": "unsupported payload"}, status=400)

        started = self._start()
        return web.json_response({
            "ok": True,
            "started": started,
            "running": True,
        }, status=202)

    def _start(self) -> bool:
        with self._lock:
            if self.running():
                return False
            self._thread = threading.Thread(target=self._run, name="flourn-executor", daemon=True)
            self._thread.start()
            return True

    def _run(self) -> None:
        try:
            self._runner()
            self._last_error = None
        except Exception as exc:
            self._last_error = str(exc)
            raise


def create_app(validate_config: bool = True) -> web.Application:
    if validate_config:
        load_config()

    controller = DrainController()
    app = web.Application()
    app.router.add_get("/health", controller.health)
    app.router.add_post("/drain", controller.drain)
    return app


async def start_server(host: str = "127.0.0.1", port: int = 19080) -> web.AppRunner:
    runner = web.AppRunner(create_app())
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner
