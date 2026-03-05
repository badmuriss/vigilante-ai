from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CAMERA_INDEX: int = 0
    MODEL_PATH: str = "best.pt"
    CONFIDENCE_THRESHOLD: float = 0.5
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALERT_COOLDOWN_SECONDS: int = 10
    CAMERA_WIDTH: int = 640
    CAMERA_HEIGHT: int = 480

    model_config = {"env_prefix": "VIGILANTE_"}


settings = Settings()
