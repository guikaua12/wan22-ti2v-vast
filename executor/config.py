from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ExecutorConfig:
    database_url: str
    executor_id_prefix: str
    comfyui_url: str
    idle_exit_seconds: int
    heartbeat_interval_seconds: int
    lease_seconds: int
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_bucket_name: str
    s3_endpoint_url: str
    s3_region: str


def load_config() -> ExecutorConfig:
    return ExecutorConfig(
        database_url=require_env("DATABASE_URL"),
        executor_id_prefix=os.getenv("EXECUTOR_ID_PREFIX", "vast"),
        comfyui_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:18188"),
        idle_exit_seconds=int(os.getenv("IDLE_EXIT_SECONDS", "30")),
        heartbeat_interval_seconds=int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "15")),
        lease_seconds=int(os.getenv("LEASE_SECONDS", "120")),
        s3_access_key_id=require_env("S3_ACCESS_KEY_ID"),
        s3_secret_access_key=require_env("S3_SECRET_ACCESS_KEY"),
        s3_bucket_name=require_env("S3_BUCKET_NAME"),
        s3_endpoint_url=require_env("S3_ENDPOINT_URL"),
        s3_region=os.getenv("S3_REGION", "auto"),
    )


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value
