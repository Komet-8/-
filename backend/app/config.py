"""运行配置。从环境变量 / .env 读取。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 火山方舟 / 豆包
    ark_api_key: str | None = None
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    ark_model: str = "doubao-1-5-pro-32k-250115"

    # 诊断参数
    num_questions: int = 5
    request_timeout: int = 60
    max_workers: int = 5

    # 存储
    database_url: str = "sqlite:///./aidso.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def use_real_provider(self) -> bool:
        """是否配置了真实的豆包 API Key。否则走模拟数据。"""
        return bool(self.ark_api_key and self.ark_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
