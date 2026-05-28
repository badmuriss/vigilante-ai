"""Camera tools — list cameras and report live stream health."""

from __future__ import annotations

from sqlalchemy import select

from app.chat.tools import Tool, ToolContext, ToolResult
from app.db.entities import Camera, Site


def _list_cameras(args: dict, ctx: ToolContext) -> ToolResult:
    rows = ctx.session.execute(
        select(Camera.id, Camera.name, Camera.source_kind, Camera.location, Camera.active)
        .join(Site, Site.id == Camera.site_id)
        .where(Site.tenant_id == ctx.tenant_id)
        .order_by(Camera.created_at.asc())
    ).all()
    return ToolResult(
        payload={
            "cameras": [
                {
                    "id": r[0],
                    "nome": r[1],
                    "tipo": r[2],
                    "local": r[3],
                    "ativa": bool(r[4]),
                }
                for r in rows
            ]
        }
    )


def _get_camera_status(args: dict, ctx: ToolContext) -> ToolResult:
    camera_id = str(args.get("camera_id") or "").strip()
    if not camera_id:
        return ToolResult(payload={"erro": "camera_id obrigatório"})

    cam = ctx.session.scalar(
        select(Camera)
        .join(Site, Site.id == Camera.site_id)
        .where(Camera.id == camera_id, Site.tenant_id == ctx.tenant_id)
    )
    if cam is None:
        return ToolResult(payload={"erro": "câmera não encontrada"})

    # Live health from the stream registry (lazy import avoids circular dep).
    from app.main import registry

    health = registry.get_health(camera_id)
    running = registry.is_running(camera_id)
    return ToolResult(
        payload={
            "id": cam.id,
            "nome": cam.name,
            "rodando": bool(running),
            "online": bool(health.online) if health else False,
            "ultima_falha": health.last_error if health else None,
            "reconexoes": health.reconnect_count if health else 0,
        }
    )


CAMERA_TOOLS = [
    Tool(
        name="list_cameras",
        description="Lista as câmeras do tenant com id, nome, tipo, local e se estão ativas.",
        parameters={"type": "object", "properties": {}},
        handler=_list_cameras,
    ),
    Tool(
        name="get_camera_status",
        description="Estado ao vivo de uma câmera (rodando, online, reconexões, última falha).",
        parameters={
            "type": "object",
            "properties": {
                "camera_id": {"type": "string", "description": "ID da câmera."}
            },
            "required": ["camera_id"],
        },
        handler=_get_camera_status,
    ),
]
