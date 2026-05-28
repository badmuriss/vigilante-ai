"""Live operational tools — alert counts/rankings scoped to the tenant.

All queries join Camera -> Site to enforce tenant isolation, mirroring
`CameraRepository.list_for_tenant`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select

from app.chat.tools import Tool, ToolContext, ToolResult
from app.db.entities import Alert, Camera, Site


def _since(hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _confirmed_only(stmt):
    # Confirmed = feedback 'correct'. Pending/rejected excluded from ops stats.
    return stmt.where(Alert.feedback == "correct")


def _summarize_today(args: dict, ctx: ToolContext) -> ToolResult:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    base = (
        select(func.count())
        .select_from(Alert)
        .join(Camera, Camera.id == Alert.camera_id)
        .join(Site, Site.id == Camera.site_id)
        .where(Site.tenant_id == ctx.tenant_id, Alert.timestamp >= start)
    )
    total = ctx.session.scalar(base) or 0
    confirmed = ctx.session.scalar(_confirmed_only(base)) or 0

    by_type = ctx.session.execute(
        select(Alert.violation_type, func.count())
        .join(Camera, Camera.id == Alert.camera_id)
        .join(Site, Site.id == Camera.site_id)
        .where(Site.tenant_id == ctx.tenant_id, Alert.timestamp >= start)
        .group_by(Alert.violation_type)
    ).all()

    top = ctx.session.execute(
        select(Camera.name, func.count())
        .join(Site, Site.id == Camera.site_id)
        .join(Alert, Alert.camera_id == Camera.id)
        .where(Site.tenant_id == ctx.tenant_id, Alert.timestamp >= start)
        .group_by(Camera.name)
        .order_by(desc(func.count()))
        .limit(3)
    ).all()

    return ToolResult(
        payload={
            "periodo": "hoje",
            "total_alertas": int(total),
            "confirmados": int(confirmed),
            "por_tipo": {row[0]: int(row[1]) for row in by_type},
            "top_cameras": [{"camera": r[0], "alertas": int(r[1])} for r in top],
        }
    )


def _get_recent_alerts(args: dict, ctx: ToolContext) -> ToolResult:
    limit = max(1, min(int(args.get("limit", 10)), 50))
    stmt = (
        select(Alert.timestamp, Alert.violation_type, Alert.confidence, Camera.name)
        .join(Camera, Camera.id == Alert.camera_id)
        .join(Site, Site.id == Camera.site_id)
        .where(Site.tenant_id == ctx.tenant_id)
    )
    camera_id = args.get("camera_id")
    if camera_id:
        stmt = stmt.where(Camera.id == str(camera_id))
    stmt = stmt.order_by(desc(Alert.timestamp)).limit(limit)
    rows = ctx.session.execute(stmt).all()
    return ToolResult(
        payload={
            "alertas": [
                {
                    "horario": r[0].isoformat() if r[0] else None,
                    "tipo": r[1],
                    "confianca": round(float(r[2]), 2),
                    "camera": r[3],
                }
                for r in rows
            ]
        }
    )


def _top_cameras_by_alerts(args: dict, ctx: ToolContext) -> ToolResult:
    period_hours = max(1, min(int(args.get("period_hours", 168)), 24 * 90))
    rows = ctx.session.execute(
        select(Camera.name, func.count())
        .join(Site, Site.id == Camera.site_id)
        .join(Alert, Alert.camera_id == Camera.id)
        .where(Site.tenant_id == ctx.tenant_id, Alert.timestamp >= _since(period_hours))
        .group_by(Camera.name)
        .order_by(desc(func.count()))
        .limit(10)
    ).all()
    return ToolResult(
        payload={
            "periodo_horas": period_hours,
            "ranking": [
                {"posicao": i, "camera": r[0], "alertas": int(r[1])}
                for i, r in enumerate(rows, start=1)
            ],
        }
    )


ALERT_TOOLS = [
    Tool(
        name="summarize_today",
        description=(
            "Resumo dos alertas de EPI de hoje no tenant: total, confirmados, "
            "quebra por tipo de violação e as câmeras com mais ocorrências."
        ),
        parameters={"type": "object", "properties": {}},
        handler=_summarize_today,
    ),
    Tool(
        name="get_recent_alerts",
        description=(
            "Lista os alertas mais recentes do tenant (opcionalmente de uma "
            "câmera específica), com horário, tipo, confiança e câmera."
        ),
        parameters={
            "type": "object",
            "properties": {
                "camera_id": {
                    "type": "string",
                    "description": "ID opcional da câmera para filtrar.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Quantos alertas retornar (máx 50).",
                },
            },
        },
        handler=_get_recent_alerts,
    ),
    Tool(
        name="top_cameras_by_alerts",
        description=(
            "Ranking das câmeras com mais alertas num período (em horas, padrão "
            "168 = 7 dias). Use para 'qual câmera flagra mais'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "period_hours": {
                    "type": "integer",
                    "description": "Janela em horas (padrão 168).",
                }
            },
        },
        handler=_top_cameras_by_alerts,
    ),
]
