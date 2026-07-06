from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Telegram Configuration
    telegram_bot_token: str = Field(..., validation_alias="TELEGRAM_BOT_TOKEN")
    
    # FastAPI Server Configuration
    app_name: str = Field("Market Intelligence Engine", validation_alias="APP_NAME")
    app_version: str = Field("0.1.0", validation_alias="APP_VERSION")
    debug: bool = Field(False, validation_alias="DEBUG")
    host: str = Field("0.0.0.0", validation_alias="HOST")
    port: int = Field(8000, validation_alias="PORT")
    
    # Logging Configuration
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    log_file: str = Field("logs/app.log", validation_alias="LOG_FILE")
    
    # Modern Pydantic v2 settings management configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
