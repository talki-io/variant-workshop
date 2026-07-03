from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量 / .env 读取配置（见 .env.example）。"""

    database_url: str = "postgresql+psycopg://app:app@db:5432/imitator"
    jwt_secret: str = "dev-insecure-secret"
    jwt_expire_minutes: int = 720
    jwt_algorithm: str = "HS256"
    anthropic_api_key: str = ""  # 从 .env 注入；绝不硬编码（§7 P1-4）
    use_real_llm: bool = False   # True 时走真实 Anthropic 管线；测试以 env 强制关闭保持离线
    crawl_scheduler_enabled: bool = False  # True 时后台定时抓取启用的 RSS 源

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
