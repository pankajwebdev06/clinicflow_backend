from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ClinicFlow API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # DATABASE_URL: str = "sqlite:///./clinicflow.db" # Default to sqlite for local dev
    DATABASE_URL: str = "sqlite:///./clinicflow.db"
    
    # Security
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_HERE_PLEASE_CHANGE"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8 # 8 days

    class Config:
        env_file = ".env"

settings = Settings()
