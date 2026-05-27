import os
from contextlib import asynccontextmanager

from vastai import BenchmarkConfig, HandlerConfig, Worker, WorkerConfig

from executor.server import start_server


ADAPTER_PORT = int(os.getenv("FLOURN_EXECUTOR_ADAPTER_PORT", "19080"))


@asynccontextmanager
async def lifecycle():
    runner = await start_server(port=ADAPTER_PORT)
    try:
        yield
    finally:
        await runner.cleanup()


worker_config = WorkerConfig(
    model_server_url="http://127.0.0.1",
    model_server_port=ADAPTER_PORT,
    model_healthcheck_url="/health",
    lifecycle=lifecycle(),
    handlers=[
        HandlerConfig(
            route="/drain",
            allow_parallel_requests=False,
            max_queue_time=5.0,
            benchmark_config=BenchmarkConfig(
                dataset=[{"kind": "drain_queue"}],
                runs=1,
                concurrency=1,
                do_warmup=False,
            ),
            workload_calculator=lambda _payload: 1.0,
        )
    ],
)


if __name__ == "__main__":
    Worker(worker_config).run()
