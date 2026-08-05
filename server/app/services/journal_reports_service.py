from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.journal_report_partner import PARTNER_REPORT_LLM_INSTRUCTIONS
from app.constants.journal_report_system_prompt import SYSTEM_PROMPT
from app.database import User, UserActionJournal
from app.schemas import (
    JournalReportGenerateRequest,
    JournalReportMetadata,
    JournalReportUserIdentity,
    JournalStructuredReport,
    JournalStructuredReportContent,
)


def _maybe_truncate_for_llm(
    log_lines: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str | None]:
    """Par défaut, tout ce que `max_entries` a ramené. Optionnel : plafond via env."""
    raw = os.environ.get("JOURNAL_REPORT_LLM_MAX_LINES", "").strip()
    if not raw:
        return log_lines, None
    try:
        cap = max(10, min(2000, int(raw)))
    except ValueError:
        return log_lines, None
    total = len(log_lines)
    if total <= cap:
        return log_lines, None
    return log_lines[:cap], (
        f"Note : échantillon des {cap} entrées les plus récentes parmi {total} "
        "sélectionnées (JOURNAL_REPORT_LLM_MAX_LINES)."
    )


def _row_to_dict(row: UserActionJournal) -> dict[str, Any]:
    out: dict[str, Any] = {
        "timestamp": row.timestamp,
        "log_date": row.log_date,
        "username": row.username,
        "action": row.action,
        "label": row.label,
        "route": row.route,
    }
    if row.payload_json:
        out["payload_excerpt"] = (
            (row.payload_json[:2000] + "…")
            if len(row.payload_json) > 2000
            else row.payload_json
        )
    return out


def _fetch_entries(
    db: Session,
    body: JournalReportGenerateRequest,
    *,
    user_id: int | None = None,
) -> list[UserActionJournal]:
    stmt = select(UserActionJournal).order_by(UserActionJournal.timestamp.desc())
    if user_id is not None:
        stmt = stmt.where(UserActionJournal.user_id == user_id)
    if body.log_date_from:
        stmt = stmt.where(UserActionJournal.log_date >= body.log_date_from)
    if body.log_date_to:
        stmt = stmt.where(UserActionJournal.log_date <= body.log_date_to)
    stmt = stmt.limit(body.max_entries)
    return list(db.scalars(stmt).all())


def _build_metadata(
    body: JournalReportGenerateRequest,
    generator_label: str | None,
) -> JournalReportMetadata:
    pf = body.log_date_from or "…"
    pt = body.log_date_to or "…"
    return JournalReportMetadata(
        period_covered=f"du {pf} au {pt}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        generated_by=generator_label or "Système automatisé",
    )


def _build_subject_identity(
    subject_user: User | None,
    *,
    single_user_scope: bool,
) -> JournalReportUserIdentity:
    if single_user_scope and subject_user is not None:
        email_part = f" — {subject_user.email}" if subject_user.email else ""
        return JournalReportUserIdentity(
            identifier_line=(
                f"Identifiant interne : {subject_user.id} — "
                f"{subject_user.username}{email_part}"
            ),
            role_and_permissions=(
                "Administrateur" if subject_user.is_admin else "Utilisateur"
            ),
            account_status="Actif",
        )
    return JournalReportUserIdentity(
        identifier_line=(
            "Rapport agrégé : activités de tous les utilisateurs "
            "correspondant aux filtres."
        ),
        role_and_permissions="—",
        account_status="—",
    )


def _assemble_full_report(
    content: JournalStructuredReportContent,
    body: JournalReportGenerateRequest,
    generator_label: str | None,
    subject_user: User | None,
    single_user_scope: bool,
) -> JournalStructuredReport:
    return JournalStructuredReport(
        metadata=_build_metadata(body, generator_label),
        subject_identity=_build_subject_identity(
            subject_user, single_user_scope=single_user_scope
        ),
        **content.model_dump(),
    )


def _empty_report(
    body: JournalReportGenerateRequest,
    generator_label: str | None,
    subject_user: User | None,
    single_user_scope: bool,
) -> JournalStructuredReport:
    pf = body.log_date_from or "…"
    pt = body.log_date_to or "…"
    period_line = f"Période demandée : {pf} → {pt} — 0 entrée analysée."
    title = "Aucune activité sur la période"
    summary = (
        "Aucune entrée de journal ne correspond aux critères "
        "(dates et compte). Élargissez la période ou utilisez "
        "l’application pour générer des traces."
    )
    high_risk = [
        "Aucun fait saillant : aucune trace enregistrée sur la période et "
        "le périmètre sélectionné.",
    ]
    activity = [
        "Aucune observation d’activité : le journal est vide pour ces dates.",
    ]
    usage = [
        "Aucune synthèse d’usage : absence d’entrées exploitables.",
    ]
    model_notes = [
        "Aucune donnée modèle issue du journal sur cette période.",
    ]
    recs = [
        "Vérifier les dates sélectionnées.",
        "Consulter la carte et les modèles pour alimenter le journal.",
    ]

    c = JournalStructuredReportContent(
        title=title,
        summary=summary,
        period_description=period_line,
        high_risk_events=high_risk,
        user_activity_notes=activity,
        recommendations=recs,
        usage_overview_bullets=usage,
        detailed_events=[],
        optional_model_data_notes=model_notes,
    )
    return _assemble_full_report(
        c, body, generator_label, subject_user, single_user_scope
    )


def _build_prompt(
    log_lines: list[dict[str, Any]],
    *,
    sample_note: str | None = None,
) -> str:
    payload = json.dumps(log_lines, ensure_ascii=False, indent=2)
    intro = f"{SYSTEM_PROMPT}{PARTNER_REPORT_LLM_INSTRUCTIONS}\n\n"
    if sample_note:
        intro += f"{sample_note}\n\n"
    intro += "Données :\n"
    return f"{intro}{payload}"


def generate_journal_structured_report(
    db: Session,
    body: JournalReportGenerateRequest,
    *,
    user_id: int | None = None,
    generator_label: str | None = None,
    subject_user: User | None = None,
) -> JournalStructuredReport:
    single_user_scope = user_id is not None
    entries = _fetch_entries(db, body, user_id=user_id)
    if not entries:
        return _empty_report(body, generator_label, subject_user, single_user_scope)

    log_lines = [_row_to_dict(e) for e in entries]
    log_lines, sample_note = _maybe_truncate_for_llm(log_lines)
    prompt = _build_prompt(log_lines, sample_note=sample_note)

    # Import paresseux : évite un cycle journal_reports ↔ journal_reports_service
    from app.services.journal_reports.factory import get_journal_report_backend

    backend = get_journal_report_backend()
    content = backend.generate_structured(
        prompt=prompt,
        output_model=JournalStructuredReportContent,
    )
    return _assemble_full_report(
        content,
        body,
        generator_label,
        subject_user,
        single_user_scope,
    )
