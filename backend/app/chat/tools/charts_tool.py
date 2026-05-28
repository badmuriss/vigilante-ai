"""Chart generation tool.

Builds a renderable chart spec (bar/line/pie) from the tenant's confirmed
alerts. The spec is emitted as a ToolResult *artifact* (the UI renders it with
recharts); a compact textual summary goes into `payload` so the LLM can also
describe the chart in words.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select

from app.chat.tools import Tool, ToolContext, ToolResult
from app.db.entities import Alert, Camera, Site

_DIMENSIONS = {"day", "violation_type", "camera"}
_DEFAULT_CHART = {"day": "line", "violation_type": "pie", "camera": "bar"}
_TITLES = {
    "day": "Alertas confirmados por dia",
    "violation_type": "Alertas por tipo de violação",
    "camera": "Alertas por câmera",
}


def _tenant_alerts_stmt(tenant_id: str, since: datetime):
    return (
        select(Alert)
        .join(Camera, Camera.id == Alert.camera_id)
        .join(Site, Site.id == Camera.site_id)
        .where(
            Site.tenant_id == tenant_id,
            Alert.feedback == "correct",
            Alert.timestamp >= since,
        )
    )


def _generate_chart(args: dict, ctx: ToolContext) -> ToolResult:
    dimension = str(args.get("dimension", "day")).strip()
    if dimension not in _DIMENSIONS:
        dimension = "day"
    period_days = max(1, min(int(args.get("period_days", 30)), 365))
    chart_type = str(args.get("chart_type") or _DEFAULT_CHART[dimension]).strip()
    if chart_type not in {"bar", "line", "pie"}:
        chart_type = _DEFAULT_CHART[dimension]

    since = datetime.now(timezone.utc) - timedelta(days=period_days)
    session = ctx.session

    data: list[dict] = []
    if dimension == "day":
        bucket = func.date_trunc("day", Alert.timestamp).label("bucket")
        rows = session.execute(
            _tenant_alerts_stmt(ctx.tenant_id, since)
            .with_only_columns(bucket, func.count())
            .group_by(bucket)
            .order_by(bucket.asc())
        ).all()
        data = [
            {"label": r[0].strftime("%d/%m") if r[0] else "?", "value": int(r[1])}
            for r in rows
        ]
    elif dimension == "violation_type":
        rows = session.execute(
            _tenant_alerts_stmt(ctx.tenant_id, since)
            .with_only_columns(Alert.violation_type, func.count())
            .group_by(Alert.violation_type)
            .order_by(desc(func.count()))
        ).all()
        data = [{"label": r[0] or "?", "value": int(r[1])} for r in rows]
    else:  # camera
        rows = session.execute(
            select(Camera.name, func.count())
            .join(Site, Site.id == Camera.site_id)
            .join(Alert, Alert.camera_id == Camera.id)
            .where(
                Site.tenant_id == ctx.tenant_id,
                Alert.feedback == "correct",
                Alert.timestamp >= since,
            )
            .group_by(Camera.name)
            .order_by(desc(func.count()))
            .limit(15)
        ).all()
        data = [{"label": r[0], "value": int(r[1])} for r in rows]

    total = sum(d["value"] for d in data)
    chart = {
        "kind": "chart",
        "chart_type": chart_type,
        "title": f"{_TITLES[dimension]} (últimos {period_days} dias)",
        "data": data,
    }
    summary = {
        "dimension": dimension,
        "period_days": period_days,
        "total_pontos": len(data),
        "total_alertas": total,
        "amostra": data[:8],
        "nota": "Um gráfico foi gerado e exibido ao usuário na interface.",
    }
    return ToolResult(payload=summary, artifacts=[chart])


CHART_TOOLS = [
    Tool(
        name="generate_chart",
        description=(
            "Gera um gráfico (renderizado na interface) a partir dos alertas "
            "confirmados do tenant. Use quando o usuário pedir gráfico, visual, "
            "evolução, distribuição ou comparação. Dimensões: 'day' (evolução "
            "diária), 'violation_type' (distribuição por tipo), 'camera' (ranking "
            "por câmera)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "dimension": {
                    "type": "string",
                    "enum": ["day", "violation_type", "camera"],
                    "description": "O que agrupar/plotar.",
                },
                "period_days": {
                    "type": "integer",
                    "description": "Janela em dias (padrão 30, máx 365).",
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie"],
                    "description": "Tipo de gráfico (opcional; há um padrão por dimensão).",
                },
            },
            "required": ["dimension"],
        },
        handler=_generate_chart,
    )
]
