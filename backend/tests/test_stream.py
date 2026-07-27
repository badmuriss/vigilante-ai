"""Tests for StreamProcessor lifecycle, thread safety, FPS throttling, and EPI filtering.

Covers: BUG-01 (stop/start crash), BUG-02 (thread safety), MODL-03 (FPS cap),
        CONF-03 (EPI filter in stream processing).

EPI scope is capacete + colete only (2-class model, see app/detector.py).
"""

from __future__ import annotations

import threading
import time
from typing import Callable

import pytest

from unittest.mock import PropertyMock

from app import stream as stream_mod
from app.config import settings
from app.models import Detection
from app.stream import StreamProcessor, _absence_implies_violation, _evaluate_person

# Person tall enough for the head zone to count as visible
# (py1 > HEAD_VISIBLE_TOP_MARGIN_PX, height >= HEAD_VISIBLE_MIN_PERSON_HEIGHT_PX).
# head zone  = y 50..170, torso zone = y 130..330.
PERSON_BBOX = (100, 50, 300, 450)
HELMET_DET = Detection(class_name="capacete", confidence=0.9, bbox=(150, 60, 250, 120))
VEST_DET = Detection(class_name="colete", confidence=0.85, bbox=(150, 150, 250, 300))
# Positive evidence of violations, from the 4-class model.
BARE_HEAD_DET = Detection(
    class_name="cabeca_descoberta", confidence=0.8, bbox=(150, 60, 250, 120)
)
NO_VEST_DET = Detection(
    class_name="sem_colete", confidence=0.8, bbox=(150, 150, 250, 300)
)


def _wait_for(pred: Callable[[], object], what: str, timeout: float = 3.0) -> None:
    """Poll until pred() is truthy. Keeps stream tests fast without racing."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return
        time.sleep(0.02)
    raise AssertionError(f"timed out after {timeout}s waiting for {what}")


@pytest.fixture()
def fast_smoothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Collapse the 5s/1.5s temporal smoothing windows so alert tests stay
    sub-second. Order is preserved (present commits before missing)."""
    monkeypatch.setattr(stream_mod, "SMOOTHING_TO_MISSING_S", 0.15)
    monkeypatch.setattr(stream_mod, "SMOOTHING_TO_PRESENT_S", 0.05)


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
        call_count = 0

        # Signature must mirror SafetyDetector.detect (frame, color_palettes=...)
        # or the process thread dies on a TypeError and counts zero frames.
        def counting_detect(frame, color_palettes=None):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            return []

        stream_processor._detector.detect = counting_detect  # type: ignore[assignment]

        stream_processor.start()
        time.sleep(1.2)  # Run for slightly over 1 second
        stream_processor.stop()

        assert 18 <= call_count <= 32, (
            f"Expected ~25 FPS, got {call_count} frames in ~1.2s. "
            f"FPS throttling may not be working."
        )


class TestEpiFilter:
    """CONF-03: active_epis gates which EPI classes are evaluated and drawn.

    The filter lives in _evaluate_person now (per-person compliance) instead of
    trimming the detection list before a scene-level annotate_frame call.
    """

    def test_epi_filter(self) -> None:
        """With active={'capacete'}, only the capacete detection is considered."""
        ev, checkable = _evaluate_person(
            PERSON_BBOX, [HELMET_DET, VEST_DET], {"capacete"}
        )

        assert checkable == {"capacete"}
        assert ev.present == {"capacete"}
        assert ev.missing == set()
        # `matched` is what gets drawn inside the person box.
        assert [d.class_name for d in ev.matched] == ["capacete"]

    def test_epi_filter_empty(self) -> None:
        """With an empty active set, nothing is evaluated, drawn or flagged."""
        ev, checkable = _evaluate_person(PERSON_BBOX, [HELMET_DET, VEST_DET], set())

        assert checkable == set()
        assert ev.present == set()
        assert ev.missing == set()
        assert ev.matched == []

    def test_epi_filter_live_toggle(
        self, stream_processor: StreamProcessor, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Changing active_epis mid-stream takes effect on the next frame."""
        stream_processor._detector.detect.return_value = [HELMET_DET, VEST_DET]  # type: ignore[attr-defined]
        stream_processor._detector.detect_persons.return_value = [PERSON_BBOX]  # type: ignore[attr-defined]

        seen: list[set[str]] = []
        real_evaluate = stream_mod._evaluate_person

        def recording_evaluate(person_bbox, ppe_dets, active, *args):  # type: ignore[no-untyped-def]
            seen.append(set(active))
            return real_evaluate(person_bbox, ppe_dets, active, *args)

        monkeypatch.setattr(stream_mod, "_evaluate_person", recording_evaluate)

        stream_processor.set_active_epis({"capacete"})
        stream_processor.start()
        try:
            _wait_for(lambda: {"capacete"} in seen, "frame evaluated with capacete")
            stream_processor.set_active_epis({"colete"})
            _wait_for(lambda: {"colete"} in seen, "frame evaluated with colete")
        finally:
            stream_processor.stop()


class TestMissingEpiAlerts:
    """Alert generation for missing EPIs in stream processing.

    Alerts are per-person now: they need a person bbox from detect_persons and
    a smoothed status commit, hence the fast_smoothing fixture.
    """

    def test_alert_uses_portuguese_label(  # type: ignore[no-untyped-def]
        self, stream_processor: StreamProcessor, alert_manager, fast_smoothing: None
    ) -> None:
        """Alerts name the missing EPI with its Portuguese label."""
        # Vest worn, helmet never seen -> capacete is the missing one.
        stream_processor._detector.detect.return_value = [VEST_DET]  # type: ignore[attr-defined]
        stream_processor._detector.detect_persons.return_value = [PERSON_BBOX]  # type: ignore[attr-defined]

        stream_processor.set_active_epis({"capacete", "colete"})
        stream_processor.start()
        try:
            # Read alerts BEFORE stop (stop resets alerts per CONTEXT.md decision)
            _wait_for(alert_manager.get_alerts, "alert for missing capacete")
            alerts = alert_manager.get_alerts()
        finally:
            stream_processor.stop()

        assert alerts[0].missing_epis == ["Capacete"]
        assert "Capacete" in alerts[0].violation_type
        assert "ausente" in alerts[0].violation_type.lower()

    def test_missing_epi_alert(  # type: ignore[no-untyped-def]
        self, stream_processor: StreamProcessor, alert_manager, fast_smoothing: None
    ) -> None:
        """When one active EPI is detected but another is absent, alert for the missing one."""
        stream_processor._detector.detect.return_value = [HELMET_DET]  # type: ignore[attr-defined]
        stream_processor._detector.detect_persons.return_value = [PERSON_BBOX]  # type: ignore[attr-defined]

        stream_processor.set_active_epis({"capacete", "colete"})
        stream_processor.start()
        try:
            _wait_for(alert_manager.get_alerts, "alert for missing colete")
            alerts = alert_manager.get_alerts()
        finally:
            stream_processor.stop()

        assert alerts[0].missing_epis == ["Colete"]
        assert "Colete" in alerts[0].violation_type

    def test_no_alert_empty_frame(  # type: ignore[no-untyped-def]
        self, stream_processor: StreamProcessor, alert_manager, fast_smoothing: None
    ) -> None:
        """No person and no EPI in frame -> no missing EPI alerts."""
        stream_processor._detector.detect.return_value = []  # type: ignore[attr-defined]

        stream_processor.set_active_epis({"capacete", "colete"})
        stream_processor.start()
        try:
            time.sleep(0.4)  # > SMOOTHING_TO_MISSING_S under fast_smoothing
            alerts = alert_manager.get_alerts()  # before stop(), which resets
        finally:
            stream_processor.stop()

        assert len(alerts) == 0, (
            f"Expected no alerts when no EPIs detected, got {len(alerts)}"
        )


ACTIVE = {"capacete", "colete"}
# Median worker height in the real CCTV footage is 58px — below
# HEAD_VISIBLE_MIN_PERSON_HEIGHT_PX, which disables the helmet check.
SHORT_PERSON_BBOX = (100, 300, 140, 358)
SHORT_BARE_HEAD_DET = Detection(
    class_name="cabeca_descoberta", confidence=0.8, bbox=(105, 300, 135, 314)
)


def _enable_violation_classes(processor: StreamProcessor) -> None:
    """Make the mocked detector look like the 4-class weights."""
    type(processor._detector).has_violation_classes = PropertyMock(return_value=True)


class TestPositiveEvidenceViolations:
    """A violation must be SEEN, not inferred from the silence of the PPE
    detector. Absence-inference measured a 100% helmet false alarm rate on
    compliant CCTV footage (ml/eval_compliant.py)."""

    def test_bare_head_detection_is_a_violation(self) -> None:
        ev, _ = _evaluate_person(
            PERSON_BBOX, [VEST_DET, BARE_HEAD_DET], ACTIVE,
            absence_implies_violation=False,
        )

        assert ev.violated == {"capacete"}
        assert ev.missing == {"capacete"}
        assert ev.present == {"colete"}
        # The bare-head box is evidence, never drawn as worn PPE.
        assert [d.class_name for d in ev.matched] == ["colete"]

    def test_no_vest_detection_is_a_violation(self) -> None:
        ev, _ = _evaluate_person(
            PERSON_BBOX, [HELMET_DET, NO_VEST_DET], ACTIVE,
            absence_implies_violation=False,
        )

        assert ev.missing == {"colete"}
        assert ev.present == {"capacete"}

    def test_undetected_helmet_is_not_a_violation(self) -> None:
        """Nothing on the head at all: no helmet box AND no bare-head box.
        Positive-evidence mode stays silent — this is the false alarm."""
        ev, _ = _evaluate_person(
            PERSON_BBOX, [VEST_DET], ACTIVE, absence_implies_violation=False,
        )

        assert ev.violated == set()
        assert ev.missing == set()

    def test_absence_fallback_still_flags_undetected_helmet(self) -> None:
        """Legacy behaviour on the old 2-class weights, unchanged."""
        ev, _ = _evaluate_person(
            PERSON_BBOX, [VEST_DET], ACTIVE, absence_implies_violation=True,
        )

        assert ev.missing == {"capacete"}
        assert ev.violated == set()

    def test_violation_bypasses_head_visibility_gate(self) -> None:
        """A person shorter than HEAD_VISIBLE_MIN_PERSON_HEIGHT_PX is undecidable
        by absence, but seeing the bare head proves the head is visible."""
        ev_absence, checkable_absence = _evaluate_person(
            SHORT_PERSON_BBOX, [], ACTIVE, absence_implies_violation=True,
        )
        assert "capacete" not in checkable_absence
        assert ev_absence.missing == {"colete"}  # torso still decidable

        ev_positive, checkable_positive = _evaluate_person(
            SHORT_PERSON_BBOX, [SHORT_BARE_HEAD_DET], ACTIVE,
            absence_implies_violation=False,
        )
        assert "capacete" in checkable_positive
        assert ev_positive.missing == {"capacete"}


class TestAbsenceModeResolution:
    """config.ABSENCE_IMPLIES_VIOLATION: auto follows the loaded weights."""

    def test_auto_follows_model_capability(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "ABSENCE_IMPLIES_VIOLATION", "auto")

        legacy = type("D", (), {"has_violation_classes": False})()
        four_class = type("D", (), {"has_violation_classes": True})()

        assert _absence_implies_violation(legacy) is True
        assert _absence_implies_violation(four_class) is False

    def test_forced_modes_override_the_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        four_class = type("D", (), {"has_violation_classes": True})()

        monkeypatch.setattr(settings, "ABSENCE_IMPLIES_VIOLATION", "on")
        assert _absence_implies_violation(four_class) is True

        monkeypatch.setattr(settings, "ABSENCE_IMPLIES_VIOLATION", "off")
        assert _absence_implies_violation(four_class) is False

    def test_detector_without_the_attribute_degrades_to_legacy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "ABSENCE_IMPLIES_VIOLATION", "auto")

        assert _absence_implies_violation(object()) is True  # type: ignore[arg-type]


class TestPositiveEvidenceAlerts:
    """End-to-end through StreamProcessor with the 4-class model."""

    def test_bare_head_triggers_alert(  # type: ignore[no-untyped-def]
        self, stream_processor: StreamProcessor, alert_manager, fast_smoothing: None
    ) -> None:
        _enable_violation_classes(stream_processor)
        stream_processor._detector.detect.return_value = [VEST_DET, BARE_HEAD_DET]  # type: ignore[attr-defined]
        stream_processor._detector.detect_persons.return_value = [PERSON_BBOX]  # type: ignore[attr-defined]

        stream_processor.set_active_epis(ACTIVE)
        stream_processor.start()
        try:
            _wait_for(alert_manager.get_alerts, "alert for bare head")
            alerts = alert_manager.get_alerts()
        finally:
            stream_processor.stop()

        assert alerts[0].missing_epis == ["Capacete"]
        assert "Capacete" in alerts[0].violation_type

    def test_undetected_helmet_triggers_no_alert(  # type: ignore[no-untyped-def]
        self, stream_processor: StreamProcessor, alert_manager, fast_smoothing: None
    ) -> None:
        """Same frame as test_alert_uses_portuguese_label (vest worn, helmet
        never detected) — with the 4-class model this is NOT an alert."""
        _enable_violation_classes(stream_processor)
        stream_processor._detector.detect.return_value = [VEST_DET]  # type: ignore[attr-defined]
        stream_processor._detector.detect_persons.return_value = [PERSON_BBOX]  # type: ignore[attr-defined]

        stream_processor.set_active_epis(ACTIVE)
        stream_processor.start()
        try:
            time.sleep(0.5)  # > SMOOTHING_TO_MISSING_S under fast_smoothing
            alerts = alert_manager.get_alerts()
        finally:
            stream_processor.stop()

        assert alerts == [], f"absence must not alert on 4-class weights: {alerts}"

    def test_violation_classes_are_not_selectable_epis(
        self, stream_processor: StreamProcessor
    ) -> None:
        stream_processor.set_active_epis({"capacete", "cabeca_descoberta"})

        assert stream_processor.active_epis == {"capacete"}
