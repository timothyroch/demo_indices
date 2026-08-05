import json
import logging
from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request

from app.constants.feature_flags import auth_disabled
from app.database import SessionLocal, User, UserActionJournal
from app.schemas import UserActionJournalCreate

logger = logging.getLogger(__name__)


def _truncate_str(value: str | None, *, max_len: int) -> str | None:
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    if len(s) <= max_len:
        return s
    return s[:max_len]


def _serialize_payload(value: Any, *, max_len: int = 60000) -> str | None:
    try:
        serialized = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return None
    if len(serialized) <= max_len:
        return serialized
    return serialized[:max_len]


def extract_journal_request_meta(request: Request) -> dict[str, Any]:
    ip: str | None = None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()[:64] or None
    elif request.client:
        ip = (request.client.host or "")[:64] or None
    ua = request.headers.get("user-agent")
    if ua and len(ua) > 500:
        ua = ua[:500]
    return {"client_ip": ip, "user_agent": ua}


def append_user_action_journal(
    *,
    current_user: User,
    body: UserActionJournalCreate,
    request_meta: dict[str, Any] | None = None,
) -> None:
    if auth_disabled():
        return

    now = datetime.now(timezone.utc)
    day = now.date().isoformat()

    meta = request_meta or {}
    if not meta.get("client_ip"):
        logger.warning(
            "[journal] Adresse IP indisponible pour l'audit (action=%s, user=%s)",
            body.action,
            current_user.username,
        )
    if not meta.get("user_agent"):
        logger.warning(
            "[journal] User-Agent indisponible pour l'audit (action=%s, user=%s)",
            body.action,
            current_user.username,
        )

    payload_obj: dict[str, Any] = {
        "operation_status": "success",
        "request": meta,
        "client": body.model_dump(exclude_none=True),
    }
    payload_json = _serialize_payload(payload_obj)

    try:
        with SessionLocal() as db:
            db.add(
                UserActionJournal(
                    timestamp=now.isoformat(),
                    log_date=day,
                    user_id=current_user.id,
                    username=current_user.username,
                    action=body.action,
                    label=_truncate_str(body.label, max_len=200),
                    route=_truncate_str(body.route, max_len=200),
                    payload_json=payload_json,
                )
            )
            db.commit()
    except Exception as e:  # noqa: BLE001
        print(f"[journal] Failed to write user action log to DB: {e}")


def append_user_model_fetch_journal(
    *,
    current_user: User,
    model_name: str,
    route: str,
    payload: Any,
    journal_action: str = "model_fetch",
) -> None:
    if auth_disabled():
        return

    now = datetime.now(timezone.utc)
    day = now.date().isoformat()

    try:
        with SessionLocal() as db:
            db.add(
                UserActionJournal(
                    timestamp=now.isoformat(),
                    log_date=day,
                    user_id=current_user.id,
                    username=current_user.username,
                    action=journal_action,
                    label=_truncate_str(model_name, max_len=200),
                    route=_truncate_str(route, max_len=200),
                    payload_json=_serialize_payload(payload),
                )
            )
            db.commit()
    except Exception as e:  # noqa: BLE001
        print(f"[journal] Failed to write model fetch log to DB: {e}")
