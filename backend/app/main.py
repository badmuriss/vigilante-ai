from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.alerts import AlertManager
from app.camera import CameraManager
from app.config import settings
from app.detector import SafetyDetector
from app.stream import StreamProcessor

app = FastAPI(title="Vigilante.AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

camera = CameraManager()
detector = SafetyDetector()
alert_manager = AlertManager()
stream_processor = StreamProcessor(camera, detector, alert_manager)


@app.get("/api/status")
def get_status() -> dict[str, object]:
    return {
        "camera_active": camera.is_running,
        "model_loaded": detector.is_loaded,
        "fps": stream_processor.fps,
        "uptime": round(stream_processor.uptime, 1),
    }


@app.get("/api/stream")
def get_stream() -> StreamingResponse:
    return StreamingResponse(
        stream_processor.generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.post("/api/stream/start")
def start_stream() -> dict[str, bool]:
    stream_processor.start()
    return {"started": True}


@app.post("/api/stream/stop")
def stop_stream() -> dict[str, bool]:
    stream_processor.stop()
    return {"stopped": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
