from __future__ import annotations

import os

from app.services.journal_reports.backends import (
    GeminiOutlinesBackend,
    JournalReportBackend,
    MockJournalReportBackend,
)


def get_journal_report_backend() -> JournalReportBackend:
    name = os.environ.get("JOURNAL_REPORT_BACKEND", "mock").strip().lower()
    if name in {"gemini", "google"}:
        return GeminiOutlinesBackend()
    return MockJournalReportBackend()
