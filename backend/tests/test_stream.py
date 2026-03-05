"""Tests for StreamProcessor lifecycle, thread safety, and FPS throttling.

Covers: BUG-01 (stop/start crash), BUG-02 (thread safety), MODL-03 (FPS cap).
Written RED-first: these tests should FAIL against the current (unfixed) code.
"""

from __future__ import annotations

import threading
import time

import cv2
import numpy as np
import pytest

from app.stream import StreamProcessor


class TestStopStartLifecycle:
    """BUG-01: Stop then start must not crash or freeze."""

    def test_stop_start_lifecycle(self, stream_processor: StreamProcessor) -> None:
        """StreamProcessor can start, stop, then start again without error.

        After stop, generate_mjpeg yields nothing.
        After restart, generate_mjpeg yields frames.
        """
        # First start
        stream_processor.start()
        assert stream_processor.is_running
        time.sleep(0.2)

        # Stop
        stream_processor.stop()
        assert not stream_processor.is_running

        # After stop, generator should not yield anything
        gen = stream_processor.generate_mjpeg()
        frame = next(gen, None)
        assert frame is None, "Generator should yield nothing after stop"

        # Restart
        stream_processor.start()
        assert stream_processor.is_running
        time.sleep(0.2)

        # After restart, generator should yield frames
        gen2 = stream_processor.generate_mjpeg()
        frame2 = next(gen2, None)
        assert frame2 is not None, "Generator should yield frames after restart"

        # Cleanup
        stream_processor.stop()


class TestMjpegGeneratorLifecycle:
    """BUG-01 extended: generators from previous sessions must exit cleanly."""

    def test_mjpeg_generator_exits_on_stop(
        self, stream_processor: StreamProcessor
    ) -> None:
        """A generator created before stop() exits its loop after stop()."""
        stream_processor.start()
        time.sleep(0.1)

        gen = stream_processor.generate_mjpeg()
        # Consume one frame to confirm it's working
        first = next(gen, None)
        assert first is not None

        # Stop the processor
        stream_processor.stop()

        # The generator should now stop yielding within a reasonable time.
        # We give it up to 1 second (it should stop almost immediately with Event).
        deadline = time.monotonic() + 1.0
        stopped = False
        for _ in gen:
            if time.monotonic() > deadline:
                break
        else:
            stopped = True

        assert stopped, "Generator did not exit after stop() within timeout"

    def test_mjpeg_generator_epoch_mismatch(
        self, stream_processor: StreamProcessor
    ) -> None:
        """A generator from epoch N stops yielding after stop/start increments epoch."""
        stream_processor.start()
        time.sleep(0.1)

        gen = stream_processor.generate_mjpeg()
        first = next(gen, None)
        assert first is not None

        # Stop and restart (epoch should increment)
        stream_processor.stop()
        stream_processor.start()
        time.sleep(0.1)

        # Old generator should not yield frames from new epoch
        stale_frame = next(gen, None)
        assert stale_frame is None, (
            "Old generator should not yield frames after epoch change"
        )

        stream_processor.stop()


class TestThreadSafety:
    """BUG-02: Concurrent reads must not raise exceptions."""

    def test_thread_safety(self, stream_processor: StreamProcessor) -> None:
        """Concurrent reads of fps, uptime, and get_jpeg_frame while running."""
        stream_processor.start()
        time.sleep(0.1)

        errors: list[Exception] = []

        def reader() -> None:
            try:
                for _ in range(100):
                    _ = stream_processor.fps
                    _ = stream_processor.uptime
                    _ = stream_processor.get_jpeg_frame()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        stream_processor.stop()
        assert not errors, f"Thread safety errors: {errors}"


class TestFpsThrottle:
    """MODL-03: Process loop must run at ~25 FPS, not unlimited."""

    def test_fps_throttle(self, stream_processor: StreamProcessor) -> None:
        """Measure actual frame count over ~1 second, assert 18-32 range."""
        # Make mock_camera return frames instantly (no delay)
        # and mock_detector return empty detections
        # The mock_camera.get_frame already returns a fake frame instantly.

        # We need to count how many times detect is called (proxy for frames processed)
        call_count = 0
        original_detect = stream_processor._detector.detect

        def counting_detect(frame):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            return []

        stream_processor._detector.detect = counting_detect  # type: ignore[assignment]

        stream_processor.start()
        time.sleep(1.2)  # Run for slightly over 1 second
        stream_processor.stop()

        # With TARGET_FPS=25, we expect ~25 frames in 1 second (allow 18-32 range)
        assert 18 <= call_count <= 32, (
            f"Expected ~25 FPS, got {call_count} frames in ~1.2s. "
            f"FPS throttling may not be working."
        )
