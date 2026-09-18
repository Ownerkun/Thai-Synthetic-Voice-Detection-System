"""
Application settings โหลดค่าจาก .env
ปรับตาม docker-compose (api service) หรือ .env ตอนรันบนเครื่อง dev
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[
            ".env.dev",
            ".env",
        ],  # .env overrides .env.dev (local machine overrides)
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "Thai Synthetic Voice Detection API"
    application_mode: str = "DEV"  # DEV | PROD
    # ค่าเป็น string ธรรมดา (ไม่ใช่ JSON list) เพื่อให้ตั้งผ่าน env var / docker-compose ได้ง่าย
    # "*" = อนุญาตทุกโดเมน (ใช้ตอน dev เท่านั้น), หรือคั่นด้วย comma เช่น "https://app.example.com,https://admin.example.com"
    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    # --- Database ---
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/spoof_detection"

    # --- Auth / JWT ---
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 วัน

    # --- Audio / Data Cleaning (ตาม UML: AudioPreprocessor) ---
    target_sample_rate: int = 16_000
    max_duration_seconds: float = 10.0
    allowed_audio_extensions: tuple[str, ...] = (".wav", ".flac")
    max_upload_size_bytes: int = 20 * 1024 * 1024  # 20 MB กันไฟล์ผิดปกติ

    # --- Model / ONNX Runtime (ตาม UML: OnnxSpoofAnalyzer) ---
    # ถ้าไฟล์นี้ไม่มีอยู่จริง ระบบจะสลับไปใช้ MockSpoofAnalyzer โดยอัตโนมัติ
    # เพื่อให้ทีม frontend/backend พัฒนาและทดสอบ pipeline ต่อได้ทันทีระหว่างที่โมเดลยังเทรนไม่เสร็จ
    onnx_model_path: str = "/models/model.onnx"
    onnx_model_meta_path: str = "/models/model.json"
    model_version: str = "mock-v0"
    segment_samples: int = 16_000 * 4  # ค่าเริ่มต้น เผื่อ meta ไม่ได้ระบุ (4 วินาที @16kHz)
    inference_temperature: float = 1.0
    default_spoof_threshold: float = 0.5

    # --- Admin bootstrap (ใช้สร้างแอดมินคนแรกตอน startup ถ้ายังไม่มีในระบบ) ---
    bootstrap_admin_username: str | None = "admin"
    bootstrap_admin_password: str | None = (
        None  # ตั้งผ่าน env ตอน deploy จริง ไม่ hardcode รหัสผ่าน
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
