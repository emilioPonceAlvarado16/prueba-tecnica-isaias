from datetime import datetime, timezone

from app.db import repository


def now() -> datetime:
    return datetime.now(timezone.utc)


def record_step(state: dict, node: str, agent: str | None, status: str, summary: str,
                started: datetime, output: dict | None = None) -> dict:
    finished = now()
    repository.insert_step(state["onboarding_id"], node, agent, status, summary, output, started, finished)
    return {"node": node, "agent": agent, "status": status, "summary": summary,
            "started_at": started.isoformat(), "duration_ms": int((finished - started).total_seconds() * 1000)}
