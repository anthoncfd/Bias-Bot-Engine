from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Telegram Security Configuration
    telegram_bot_token: str = Field(..., validation_alias="TELEGRAM_TOKEN")
    
    # Financial Market Provider Key
    market_api_key: str = Field("demo", validation_alias="MARKET_API_KEY")
    
    # Supabase Connection Keys
    supabase_url: str = Field(..., validation_alias="SUPABASE_URL")
    supabase_key: str = Field(..., validation_alias="SUPABASE_KEY")
    
    # System Internal Parameters
    app_name: str = Field("Market Intelligence Engine", validation_alias="APP_NAME")
    app_version: str = Field("2.0.0", validation_alias="APP_VERSION")
    debug: bool = Field(False, validation_alias="DEBUG")
    host: str = Field("0.0.0.0", validation_alias="HOST")
    port: int = Field(8000, validation_alias="PORT")
    
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    log_file: str = Field("logs/app.log", validation_alias="LOG_FILE")
    
    model_config = SettingsConfigDict(extra="ignore")

settings = Settings()
