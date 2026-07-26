"""Live operational tools — alert counts/rankings scoped to the tenant.

All queries join Camera -> Site to enforce tenant isolation, mirroring
`CameraRepository.list_for_tenant`.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import desc, func, select

from app.chat.tools import Tool, ToolContext, ToolResult
from app.db.entities import Alert, Camera, Site

LOCAL_TZ = ZoneInfo("America/Sao_Paulo")


def _since(hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _local_iso(value: datetime | None) -> str | None:
    value = _as_utc(value)
    return value.astimezone(LOCAL_TZ).isoformat() if value else None


def _local_label(value: datetime | None) -> str | None:
    value = _as_utc(value)
    return value.astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M") if value else None


def _age_minutes(value: datetime | None, now: datetime | None = None) -> int | None:
    value = _as_utc(value)
    if value is None:
        return None
    now = now or _now_utc()
    return max(0, int((now - value).total_seconds() // 60))


def _confirmed_only(stmt):
    # Confirmed = feedback 'correct'. Pending/rejected excluded from ops stats.
    return stmt.where(Alert.feedback == "correct")


def _summarize_today(args: dict, ctx: ToolContext) -> ToolResult:
    now = _now_utc()
    today_local = now.astimezone(LOCAL_TZ).date()
    start = datetime.combine(today_local, time.min, tzinfo=LOCAL_TZ).astimezone(
        timezone.utc
    )
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
            "timezone": "America/Sao_Paulo",
            "agora_local": now.astimezone(LOCAL_TZ).isoformat(),
            "inicio_periodo_local": start.astimezone(LOCAL_TZ).isoformat(),
            "total_alertas": int(total),
            "confirmados": int(confirmed),
            "por_tipo": {row[0]: int(row[1]) for row in by_type},
            "top_cameras": [{"camera": r[0], "alertas": int(r[1])} for r in top],
        }
    )


def _get_recent_alerts(args: dict, ctx: ToolContext) -> ToolResult:
    limit = max(1, min(int(args.get("limit", 10)), 50))
    now = _now_utc()
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
    timestamps = [_as_utc(r[0]) for r in rows if r[0]]
    newest = max(timestamps) if timestamps else None
    oldest = min(timestamps) if timestamps else None
    newest_age = _age_minutes(newest, now)
    if newest_age is None:
        temporal_note = "Nenhum alerta encontrado."
    elif newest_age <= 30:
        temporal_note = "O alerta mais recente e de agora/ultimos minutos."
    else:
        temporal_note = (
            "Estes sao os alertas mais recentes gravados no banco, mas nao sao "
            f"de agora; o mais recente tem cerca de {newest_age} minutos."
        )
    return ToolResult(
        payload={
            "timezone": "America/Sao_Paulo",
            "agora_local": now.astimezone(LOCAL_TZ).isoformat(),
            "janela_dos_alertas_local": {
                "inicio": _local_label(oldest),
                "fim": _local_label(newest),
            },
            "idade_mais_recente_minutos": newest_age,
            "alerta_mais_recente_e_atual": bool(
                newest_age is not None and newest_age <= 30
            ),
            "observacao_temporal": temporal_note,
            "alertas": [
                {
                    "horario_utc": _as_utc(r[0]).isoformat() if r[0] else None,
                    "horario_local": _local_iso(r[0]),
                    "horario_local_legivel": _local_label(r[0]),
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
            "timezone": "America/Sao_Paulo",
            "agora_local": datetime.now(timezone.utc).astimezone(LOCAL_TZ).isoformat(),
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
            "câmera específica), com horário local America/Sao_Paulo, tipo, "
            "confiança, câmera e idade do alerta mais recente em relação a agora."
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
