from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlmodel import Field, Session, SQLModel, create_engine, select

from crawllmer.domain.models import CrawlRun, CrawlStatus, WebsiteTarget
from crawllmer.domain.ports import CrawlRunRepository


class CrawlRunRecord(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    hostname: str = Field(index=True)
    url: str
    status: str = Field(index=True)
    strategy_attempts: str = ""
    diagnostics: str = "{}"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)


class SqliteCrawlRunRepository(CrawlRunRepository):
    def __init__(self, db_url: str = "sqlite:///./crawllmer.db") -> None:
        self.engine = create_engine(db_url)
        SQLModel.metadata.create_all(self.engine)

    def create_run(self, run: CrawlRun) -> CrawlRun:
        record = CrawlRunRecord(
            id=run.id,
            hostname=run.target.hostname,
            url=str(run.target.url),
            status=run.status.value,
            strategy_attempts=",".join(run.strategy_attempts),
            diagnostics=str(run.diagnostics),
        )
        with Session(self.engine) as session:
            session.add(record)
            session.commit()
        return run

    def update_run(self, run: CrawlRun) -> CrawlRun:
        with Session(self.engine) as session:
            record = session.get(CrawlRunRecord, run.id)
            if record is None:
                return self.create_run(run)
            record.status = run.status.value
            record.strategy_attempts = ",".join(run.strategy_attempts)
            record.diagnostics = str(run.diagnostics)
            session.add(record)
            session.commit()
        return run

    def latest_runs(
        self, hostname: str | None = None, limit: int = 20
    ) -> list[CrawlRun]:
        with Session(self.engine) as session:
            statement = select(CrawlRunRecord).order_by(
                CrawlRunRecord.created_at.desc()
            )
            if hostname:
                statement = statement.where(CrawlRunRecord.hostname == hostname)
            records = session.exec(statement.limit(limit)).all()
        return [
            CrawlRun(
                id=record.id,
                target=WebsiteTarget(url=record.url, hostname=record.hostname),
                status=CrawlStatus(record.status),
                strategy_attempts=[x for x in record.strategy_attempts.split(",") if x],
                diagnostics={"raw": record.diagnostics},
            )
            for record in records
        ]

    def strategy_history(self, hostname: str) -> list[str]:
        with Session(self.engine) as session:
            statement = (
                select(CrawlRunRecord)
                .where(CrawlRunRecord.hostname == hostname)
                .where(CrawlRunRecord.status == CrawlStatus.succeeded.value)
                .order_by(CrawlRunRecord.created_at.desc())
            )
            records = session.exec(statement).all()
        ordered: list[str] = []
        for record in records:
            for attempt in record.strategy_attempts.split(","):
                if attempt and attempt not in ordered:
                    ordered.append(attempt)
        return ordered


def default_repository() -> SqliteCrawlRunRepository:
    db_path = Path("./crawllmer.db")
    return SqliteCrawlRunRepository(f"sqlite:///{db_path}")
