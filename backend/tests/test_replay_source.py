from pathlib import Path
import threading
import time

import cv2
import numpy as np

import pytest
from pydantic import ValidationError

from app.schemas import CameraCreateRequest
from app.sources import ReplaySource


def test_accepts_replay_file_inside_root(tmp_path: Path) -> None:
    replay_file = tmp_path / "canteiro.mp4"
    replay_file.write_bytes(b"video")

    source = ReplaySource(file_name=replay_file.name, root=tmp_path)

    assert source.describe() == "replay:canteiro.mp4"


def test_rejects_replay_path_outside_root(tmp_path: Path) -> None:
    outside_file = tmp_path.parent / f"{tmp_path.name}-outside.mp4"
    outside_file.write_bytes(b"video")

    with pytest.raises(ValueError, match="inside REPLAY_ROOT"):
        ReplaySource(file_name=f"../{outside_file.name}", root=tmp_path)


def test_requires_replay_file() -> None:
    with pytest.raises(ValidationError, match="replay_file is required"):
        CameraCreateRequest(name="Replay", source_kind="replay")


def test_loops_replay_at_end_without_reporting_reconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay_file = tmp_path / "canteiro.mp4"
    replay_file.write_bytes(b"video")
    source = ReplaySource(file_name=replay_file.name, root=tmp_path)
    looped = threading.Event()

    class FakeCapture:
        def __init__(self) -> None:
            self.position = 0

        def isOpened(self) -> bool:
            return True

        def read(self) -> tuple[bool, np.ndarray | None]:
            time.sleep(0.002)
            if self.position == 0:
                self.position = 1
                return True, np.zeros((2, 2, 3), dtype=np.uint8)
            return False, None

        def set(self, prop: int, value: float) -> bool:
            if prop == cv2.CAP_PROP_POS_FRAMES and value == 0:
                self.position = 0
                looped.set()
                return True
            return False

        def release(self) -> None:
            pass

    monkeypatch.setattr(source, "_open", FakeCapture)

    source.start()
    assert looped.wait(timeout=1)
    health = source.health
    source.stop()

    assert health.online is True
    assert health.reconnect_count == 0
    assert health.consecutive_failures == 0


def test_paces_replay_using_the_video_frame_rate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay_file = tmp_path / "canteiro.mp4"
    replay_file.write_bytes(b"video")
    source = ReplaySource(file_name=replay_file.name, root=tmp_path)
    sleeps: list[float] = []

    class FakeCapture:
        def get(self, prop: int) -> float:
            assert prop == cv2.CAP_PROP_FPS
            return 25.0

    monkeypatch.setattr(cv2, "VideoCapture", lambda *_args: FakeCapture())
    monkeypatch.setattr(time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(source, "_sleep", sleeps.append)

    capture = source._open()
    source._after_frame_read(capture)

    assert sleeps == pytest.approx([0.04])


def test_reconnects_when_replay_still_fails_after_reset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    replay_file = tmp_path / "canteiro.mp4"
    replay_file.write_bytes(b"video")
    source = ReplaySource(file_name=replay_file.name, root=tmp_path)
    source.INITIAL_BACKOFF = 0.001
    source.MAX_BACKOFF = 0.001
    reset_calls = 0

    class FakeCapture:
        def __init__(self) -> None:
            self.reads = 0

        def isOpened(self) -> bool:
            return True

        def read(self) -> tuple[bool, np.ndarray | None]:
            self.reads += 1
            if self.reads == 1:
                return True, np.zeros((2, 2, 3), dtype=np.uint8)
            return False, None

        def set(self, prop: int, value: float) -> bool:
            nonlocal reset_calls
            if prop == cv2.CAP_PROP_POS_FRAMES and value == 0:
                reset_calls += 1
                return True
            return False

        def release(self) -> None:
            pass

    monkeypatch.setattr(source, "_open", FakeCapture)

    source.start()
    deadline = time.monotonic() + 1
    while source.health.reconnect_count == 0 and time.monotonic() < deadline:
        time.sleep(0.005)
    health = source.health
    source.stop()

    assert health.reconnect_count >= 1
    assert reset_calls >= 1
