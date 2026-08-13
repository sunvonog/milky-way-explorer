from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MWE_", env_file=".env")

    env: str = "development"
    data_root: Path = Path("../data")
    cors_origins: list[str] = ["http://localhost:5173"]
    duckdb_memory_limit: str = "1GB"

    @property
    def processed_root(self) -> Path:
        return self.data_root / "processed"

    @property
    def frontend_root(self) -> Path:
        return self.data_root / "frontend"

    @property
    def builds_root(self) -> Path:
        return self.data_root / "builds"

    @property
    def current_pointer(self) -> Path:
        return self.builds_root / "current.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
