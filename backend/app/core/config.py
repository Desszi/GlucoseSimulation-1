try:
    from pydantic_settings import BaseSettings
except ImportError:
    # fallback for pydantic v1 environments
    from pydantic import BaseSettings  # type: ignore

class Settings(BaseSettings):
    APP_NAME: str = "GlucoseSim Backend"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "CHANGE_ME"  # később .env
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    SQLITE_URL: str = "sqlite:///./glucosesim.db"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
