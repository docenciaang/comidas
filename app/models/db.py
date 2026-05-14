from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Session, SQLModel, create_engine


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config.yaml"


class ApiConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8010
    basic_auth_user: str = "admin"
    basic_auth_password: str = "admin"


class NotificationConfig(BaseModel):
    enabled: bool = False
    ntfy_topic: str = ""


class AIConfig(BaseModel):
    provider: str = "mock"
    model: str = "family-menu-planner"
    temperature: float = 0.2


class FileConfig(BaseModel):
    app_name: str = "Gestor de Menus Familiares"
    environment: str = "development"
    database_url: str = "sqlite:///data/menu_familiar.db"
    default_servings: int = 4
    cache_dir: str = "data/cache"
    api: ApiConfig = ApiConfig()
    notifications: NotificationConfig = NotificationConfig()
    ai: AIConfig = AIConfig()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    basic_auth_user: Optional[str] = None
    basic_auth_password: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


def load_file_config() -> FileConfig:
    if not CONFIG_PATH.exists():
        return FileConfig()
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return FileConfig.model_validate(data)


def load_settings() -> Settings:
    return Settings()


def get_database_url() -> str:
    config = load_file_config()
    if config.database_url.startswith("sqlite:///") and not config.database_url.startswith("sqlite:////"):
        relative_path = config.database_url.removeprefix("sqlite:///")
        return f"sqlite:///{ROOT_DIR / relative_path}"
    return config.database_url


def ensure_data_dirs() -> None:
    config = load_file_config()
    (ROOT_DIR / "data").mkdir(parents=True, exist_ok=True)
    (ROOT_DIR / config.cache_dir).mkdir(parents=True, exist_ok=True)


ensure_data_dirs()
engine = create_engine(get_database_url(), echo=False, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)
