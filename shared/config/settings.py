from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    gm_gateway_url: str = "http://localhost:8010"
    naming_service_url: str = "http://localhost:8020"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model_naming: str = "qwen3:0.6b"
    ollama_model_people: str = "qwen3:4b"
    ollama_model_gm: str = "qwen3:14b"
    ollama_timeout: int = 20
    ollama_retries: int = 2

    sim_seed: int = 42
    world_width: int = 48
    world_height: int = 32

    scheduler_default_speed: int = 1
    scheduler_snapshot_interval: int = 10
    admin_debug_mode: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
