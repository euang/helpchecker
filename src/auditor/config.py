from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class LoginSelectors(BaseModel):
    username: str = "input[name='email']"
    password: str = "input[name='password']"
    submit: str = "button[type='submit']"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    docs_base_url: HttpUrl = Field(alias="DOCS_BASE_URL")
    app_base_url: HttpUrl = Field(alias="APP_BASE_URL")
    app_login_url: HttpUrl = Field(alias="APP_LOGIN_URL")
    app_username: str = Field(alias="APP_USERNAME")
    app_password: str = Field(alias="APP_PASSWORD")
    app_login_selectors: str = Field(alias="APP_LOGIN_SELECTORS")
    max_pages_docs: int = Field(default=500, alias="MAX_PAGES_DOCS")
    max_pages_app: int = Field(default=200, alias="MAX_PAGES_APP")
    crawl_delay_seconds: float = Field(default=1.0, alias="CRAWL_DELAY_SECONDS")
    app_spa_hydration_delay: float = Field(default=0.5, alias="APP_SPA_HYDRATION_DELAY")
    seed_routes_file: str = Field(default="seed_routes.txt", alias="SEED_ROUTES_FILE")
    storage_state_path: str = Field(default="storage_state.json", alias="STORAGE_STATE_PATH")
    artifacts_dir: str = Field(default="artifacts", alias="ARTIFACTS_DIR")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    def selectors(self) -> LoginSelectors:
        try:
            parsed = json.loads(self.app_login_selectors)
            return LoginSelectors(**parsed)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError("APP_LOGIN_SELECTORS must be valid JSON") from exc

    @property
    def storage_state(self) -> Path:
        return Path(self.storage_state_path)

    @property
    def artifacts_path(self) -> Path:
        path = Path(self.artifacts_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
