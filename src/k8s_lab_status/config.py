from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core — comma-separated list of URLs to monitor
    monitor_urls: str = ""
    check_interval: int = 30  # seconds between checks
    results_path: str = "/mnt/efs/status.json"  # EFS ReadWriteMany demo (Scenario core)

    # Scenario 7: Secrets Manager CSI Driver
    secret_path: str = "/mnt/secrets/api-key"

    # Scenario 12: Load testing — configurable response behavior
    simulate_latency_ms: int = 0  # artificial delay added to every response
    simulate_error_rate: float = 0.0  # 0.0–1.0 fraction of requests that return 500

    # App
    app_name: str = "k8s-lab-status"

    def get_urls(self) -> list[str]:
        return [u.strip() for u in self.monitor_urls.split(",") if u.strip()]
