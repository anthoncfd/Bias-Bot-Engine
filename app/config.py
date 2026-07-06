from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Fixed: Now matches your exact environment variable name (TELEGRAM_TOKEN)
    telegram_bot_token: str = Field(..., validation_alias="TELEGRAM_TOKEN")
    
    # FastAPI Server Configuration
    app_name: str = Field("Market Intelligence Engine", validation_alias="APP_NAME")
    app_version: str = Field("0.1.0", validation_alias="APP_VERSION")
    debug: bool = Field(False, validation_alias="DEBUG")
    host: str = Field("0.0.0.0", validation_alias="HOST")
    port: int = Field(8000, validation_alias="PORT")
    
    # Logging Configuration
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    log_file: str = Field("logs/app.log", validation_alias="LOG_FILE")
    
    # Configured strictly for System Environment Variables
    model_config = SettingsConfigDict(
        extra="ignore"
    )

settings = Settings()
