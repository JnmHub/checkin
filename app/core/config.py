from pydantic_settings import BaseSettings
from minio import Minio

class Settings(BaseSettings):
    # --- 基础配置 ---
    PROJECT_NAME: str = "外勤打卡系统"
    SECRET_KEY: str = "jnm_language_creator_secret_key" # 用于生成 JWT Token
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # Token 有效期暂定 7 天

    # --- MySQL 数据库配置 ---
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "123456"
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: str = "3306"
    MYSQL_DB: str = "attendance_db"

    # --- MinIO 配置 ---
    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "DD8lDpIvnnIFriKxODPZ"
    MINIO_SECRET_KEY: str = "GVPNJOgrS1hqsZLcO3mffTJCnPyc1k8wRJgDujU7"
    MINIO_BUCKET: str = "ddd"

    # --- 高德 API 配置 ---
    AMAP_WEB_KEY: str = "3b36ab78a7a40a0e1a1f3ea23400f6a8"

    class Config:
        # 告诉 Pydantic 优先读取项目根目录下的 .env 文件
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# 全局复用 MinIO 客户端 (保持单例)
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False # 开发环境通常没有 HTTPS
)