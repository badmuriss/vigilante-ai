"""Seed demo alerts for a tenant so the assistant has data to chart.

Usage (inside the backend container):
    python -m scripts.seed_demo_alerts --email demo-ui@test.com --count 180 --days 30
    # or by tenant id:
    python -m scripts.seed_demo_alerts --tenant <uuid> --count 180 --days 30

Creates a demo site + 3 cameras (if missing) and inserts confirmed alerts
(feedback='correct') spread over the past N days with realistic violation
types. Idempotent-ish: re-running adds more alerts (use --reset to wipe the
demo cameras' alerts first).
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import delete, select

from app.db.base import session_scope
from app.db.entities import Alert, Camera, Site, User

log = structlog.get_logger(__name__)

# Mirrors what the live detector produces (PT labels joined + " ausente(s)").
_VIOLATIONS = [
    ("Capacete ausente(s)", ["Capacete"], 0.45),
    ("Colete ausente(s)", ["Colete"], 0.35),
    ("Capacete, Colete ausente(s)", ["Capacete", "Colete"], 0.20),
]
_CAMERA_NAMES = ["Portão de entrada", "Pátio de descarga", "Andaime norte"]


def _resolve_tenant(session, email: str | None, tenant_id: str | None) -> str:
    if tenant_id:
        return tenant_id
    if email:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            raise SystemExit(f"No user with email {email}")
        return str(user.tenant_id)
    # Fallback: first tenant.
    user = session.scalar(select(User).limit(1))
    if user is None:
        raise SystemExit("No users in DB; register one first.")
    return str(user.tenant_id)


def _ensure_cameras(session, tenant_id: str) -> list[Camera]:
    site = session.scalar(select(Site).where(Site.tenant_id == tenant_id).limit(1))
    if site is None:
        site = Site(tenant_id=tenant_id, name="Obra Demo", location="Canteiro Central")
        session.add(site)
        session.flush()
    cameras = list(
        session.scalars(select(Camera).where(Camera.site_id == site.id)).all()
    )
    existing_names = {c.name for c in cameras}
    for name in _CAMERA_NAMES:
        if name not in existing_names:
            cam = Camera(
                site_id=site.id,
                name=name,
                source_kind="rtsp",
                rtsp_url=f"rtsp://demo/{name}",
                location=name,
                active=False,
            )
            session.add(cam)
            cameras.append(cam)
    session.flush()
    return cameras


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default="demo-ui@test.com")
    parser.add_argument("--tenant", default=None)
    parser.add_argument("--count", type=int, default=180)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--reset", action="store_true", help="wipe demo cameras' alerts first")
    args = parser.parse_args()

    weights = [w for _, _, w in _VIOLATIONS]
    now = datetime.now(timezone.utc)

    with session_scope() as session:
        tenant_id = _resolve_tenant(session, args.email, args.tenant)
        cameras = _ensure_cameras(session, tenant_id)
        cam_ids = [c.id for c in cameras]

        if args.reset:
            session.execute(delete(Alert).where(Alert.camera_id.in_(cam_ids)))
            session.flush()

        created = 0
        for _ in range(args.count):
            vtype, missing, _w = random.choices(_VIOLATIONS, weights=weights)[0]
            # Skew recent days a bit heavier so the daily chart trends.
            day_offset = int(abs(random.gauss(0, args.days / 2))) % args.days
            ts = now - timedelta(
                days=day_offset,
                hours=random.randint(6, 18),
                minutes=random.randint(0, 59),
            )
            alert = Alert(
                camera_id=random.choice(cam_ids),
                violation_type=vtype,
                confidence=round(random.uniform(0.55, 0.97), 2),
                missing_epis=missing,
                frame_path=None,
                thumbnail_path=None,
                feedback="correct",
                feedback_at=ts,
            )
            alert.timestamp = ts
            session.add(alert)
            created += 1
        session.commit()

    log.info("seed_demo_alerts_done", tenant_id=tenant_id, created=created)
    print(f"Seeded {created} confirmed alerts across {len(cam_ids)} cameras "
          f"for tenant {tenant_id} over {args.days} days.")


if __name__ == "__main__":
    main()
