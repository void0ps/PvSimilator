import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 应用配置
    app_name: str = "光伏仿真软件"
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # 数据库配置
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./pv_simulator.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # API配置
    nasa_sse_api_key: Optional[str] = os.getenv("NASA_SSE_API_KEY")
    meteonorm_api_key: Optional[str] = os.getenv("METEONORM_API_KEY")
    weather_api_key: Optional[str] = os.getenv("WEATHER_API_KEY")
    
    # 文件上传配置
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    max_upload_size: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))
    
    # CORS配置
    allowed_origins: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"

settings = Settings()