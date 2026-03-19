from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import OperationalError
from sqlmodel import Field, Session, SQLModel, create_engine, select

from crawllmer.domain.models import (
    CrawlEvent,
    CrawlRun,
    ExtractedPage,
    GenerationArtifact,
    RunStatus,
    WorkItem,
    WorkItemState,
    WorkStage,
)
from crawllmer.domain.ports import CrawlRepository


class CrawlRunRecord(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    target_url: str
    hostname: str = Field(index=True)
    status: str = Field(index=True)
    score: float | None = None
    score_breakdown: str = "{}"
    artifact_path: str | None = None
    notes: str = "{}"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    completed_at: datetime | None = None


class WorkItemRecord(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    run_id: UUID = Field(index=True)
    stage: str = Field(index=True)
    state: str = Field(index=True)
    url: str
    attempt_count: int = 0
    last_error: str | None = None
    priority: int = 100
    extra_data: str = "{}"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)


class WorkItemEventRecord(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    work_item_id: UUID = Field(index=True)
    from_state: str
    to_state: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)


class DiscoveredUrlRecord(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    run_id: UUID = Field(index=True)
    url: str = Field(index=True)
    provenance: str


class ExtractedPageRecord(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    run_id: UUID = Field(index=True)
    url: str = Field(index=True)
    title: str | None = None
    description: str | None = None
    provenance: str = "{}"
    confidence: str = "{}"


class UrlValidatorRecord(SQLModel, table=True):
    url: str = Field(primary_key=True)
    etag: str | None = None
    last_modified: str | None = None


class CrawlEventRecord(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    run_id: UUID = Field(index=True)
    name: str = Field(index=True)
    system: str = Field(index=True)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    metadata_json: str = "{}"


class ArtifactRecord(SQLModel, table=True):
    run_id: UUID = Field(primary_key=True)
    llms_txt: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SqliteCrawlRepository(CrawlRepository):
    def __init__(self, db_url: str = "sqlite:///./crawllmer.db") -> None:
        self.engine = create_engine(db_url)
        try:
            SQLModel.metadata.create_all(self.engine)
        except OperationalError:
            pass  # table already created by another process (race on startup)

    def create_run(self, run: CrawlRun) -> CrawlRun:
        record = CrawlRunRecord(
            id=run.id,
            target_url=run.target_url,
            hostname=run.hostname,
            status=run.status.value,
            score=run.score,
            score_breakdown=json.dumps(run.score_breakdown),
            artifact_path=run.artifact_path,
            notes=json.dumps(run.notes),
            created_at=run.created_at,
            completed_at=run.completed_at,
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
            record.score = run.score
            record.score_breakdown = json.dumps(run.score_breakdown)
            record.artifact_path = run.artifact_path
            record.notes = json.dumps(run.notes)
            record.completed_at = run.completed_at
            session.add(record)
            session.commit()
        return run

    def get_run(self, run_id: UUID) -> CrawlRun | None:
        with Session(self.engine) as session:
            record = session.get(CrawlRunRecord, run_id)
            if record is None:
                return None
            return self._to_run(record)

    def list_runs(self, hostname: str | None = None, limit: int = 50) -> list[CrawlRun]:
        statement = select(CrawlRunRecord).order_by(CrawlRunRecord.created_at.desc())
        if hostname:
            statement = statement.where(CrawlRunRecord.hostname == hostname)
        with Session(self.engine) as session:
            rows = session.exec(statement.limit(limit)).all()
        return [self._to_run(row) for row in rows]

    def create_work_item(self, item: WorkItem) -> WorkItem:
        record = WorkItemRecord(
            id=item.id,
            run_id=item.run_id,
            stage=item.stage.value,
            state=item.state.value,
            url=item.url,
            attempt_count=item.attempt_count,
            last_error=item.last_error,
            priority=item.priority,
            extra_data=json.dumps(item.metadata),
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        with Session(self.engine) as session:
            session.add(record)
            session.commit()
        return item

    def update_work_item(self, item: WorkItem) -> WorkItem:
        with Session(self.engine) as session:
            record = session.get(WorkItemRecord, item.id)
            if record is None:
                return self.create_work_item(item)
            previous_state = record.state
            record.state = item.state.value
            record.attempt_count = item.attempt_count
            record.last_error = item.last_error
            record.updated_at = item.updated_at
            record.extra_data = json.dumps(item.metadata)
            session.add(record)
            if previous_state != record.state:
                session.add(
                    WorkItemEventRecord(
                        id=UUID(int=item.id.int ^ item.updated_at.microsecond),
                        work_item_id=item.id,
                        from_state=previous_state,
                        to_state=record.state,
                    )
                )
            session.commit()
        return item

    def list_work_items(self, run_id: UUID) -> list[WorkItem]:
        statement = (
            select(WorkItemRecord)
            .where(WorkItemRecord.run_id == run_id)
            .order_by(WorkItemRecord.created_at.asc())
        )
        with Session(self.engine) as session:
            rows = session.exec(statement).all()
        return [
            WorkItem(
                id=row.id,
                run_id=row.run_id,
                stage=WorkStage(row.stage),
                state=WorkItemState(row.state),
                url=row.url,
                attempt_count=row.attempt_count,
                last_error=row.last_error,
                priority=row.priority,
                metadata=json.loads(row.extra_data),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def add_discovered_urls(
        self, run_id: UUID, urls: list[tuple[str, str]]
    ) -> list[str]:
        with Session(self.engine) as session:
            existing = {
                row.url
                for row in session.exec(
                    select(DiscoveredUrlRecord).where(
                        DiscoveredUrlRecord.run_id == run_id
                    )
                ).all()
            }
            inserted: list[str] = []
            for url, provenance in urls:
                if url in existing:
                    continue
                inserted.append(url)
                session.add(
                    DiscoveredUrlRecord(
                        id=UUID(int=hash((run_id, url)) & ((1 << 128) - 1)),
                        run_id=run_id,
                        url=url,
                        provenance=provenance,
                    )
                )
            session.commit()
        return inserted

    def get_discovered_urls(self, run_id: UUID) -> list[tuple[str, str]]:
        with Session(self.engine) as session:
            rows = session.exec(
                select(DiscoveredUrlRecord).where(DiscoveredUrlRecord.run_id == run_id)
            ).all()
        return [(row.url, row.provenance) for row in rows]

    def upsert_extracted_pages(self, pages: list[ExtractedPage]) -> None:
        with Session(self.engine) as session:
            for page in pages:
                rows = session.exec(
                    select(ExtractedPageRecord)
                    .where(ExtractedPageRecord.run_id == page.run_id)
                    .where(ExtractedPageRecord.url == page.url)
                ).all()
                if rows:
                    record = rows[0]
                    record.title = page.title
                    record.description = page.description
                    record.provenance = json.dumps(page.provenance)
                    record.confidence = json.dumps(page.confidence)
                    session.add(record)
                    continue
                session.add(
                    ExtractedPageRecord(
                        id=UUID(int=hash((page.run_id, page.url)) & ((1 << 128) - 1)),
                        run_id=page.run_id,
                        url=page.url,
                        title=page.title,
                        description=page.description,
                        provenance=json.dumps(page.provenance),
                        confidence=json.dumps(page.confidence),
                    )
                )
            session.commit()

    def get_extracted_pages(self, run_id: UUID) -> list[ExtractedPage]:
        with Session(self.engine) as session:
            rows = session.exec(
                select(ExtractedPageRecord).where(ExtractedPageRecord.run_id == run_id)
            ).all()
        return [
            ExtractedPage(
                run_id=row.run_id,
                url=row.url,
                title=row.title,
                description=row.description,
                provenance=json.loads(row.provenance),
                confidence=json.loads(row.confidence),
            )
            for row in rows
        ]

    def set_validator(
        self, url: str, etag: str | None, last_modified: str | None
    ) -> None:
        with Session(self.engine) as session:
            row = session.get(UrlValidatorRecord, url)
            if row is None:
                row = UrlValidatorRecord(url=url)
            row.etag = etag
            row.last_modified = last_modified
            session.add(row)
            session.commit()

    def get_validator(self, url: str) -> tuple[str | None, str | None]:
        with Session(self.engine) as session:
            row = session.get(UrlValidatorRecord, url)
            if row is None:
                return None, None
            return row.etag, row.last_modified

    def save_artifact(self, artifact: GenerationArtifact) -> None:
        with Session(self.engine) as session:
            row = ArtifactRecord(
                run_id=artifact.run_id,
                llms_txt=artifact.llms_txt,
                generated_at=artifact.generated_at,
            )
            session.merge(row)
            session.commit()

    def get_artifact(self, run_id: UUID) -> GenerationArtifact | None:
        with Session(self.engine) as session:
            row = session.get(ArtifactRecord, run_id)
            if row is None:
                return None
        return GenerationArtifact(
            run_id=row.run_id, llms_txt=row.llms_txt, generated_at=row.generated_at
        )

    def create_event(self, event: CrawlEvent) -> CrawlEvent:
        record = CrawlEventRecord(
            id=event.id,
            run_id=event.run_id,
            name=event.name,
            system=event.system,
            started_at=event.started_at,
            completed_at=event.completed_at,
            metadata_json=json.dumps(event.metadata, default=str),
        )
        with Session(self.engine) as session:
            session.add(record)
            session.commit()
        return event

    def list_events(self, run_id: UUID) -> list[CrawlEvent]:
        statement = (
            select(CrawlEventRecord)
            .where(CrawlEventRecord.run_id == run_id)
            .order_by(CrawlEventRecord.started_at.asc())
        )
        with Session(self.engine) as session:
            rows = session.exec(statement).all()
        return [
            CrawlEvent(
                id=row.id,
                run_id=row.run_id,
                name=row.name,
                system=row.system,
                started_at=row.started_at,
                completed_at=row.completed_at,
                metadata=json.loads(row.metadata_json),
            )
            for row in rows
        ]

    @staticmethod
    def _to_run(record: CrawlRunRecord) -> CrawlRun:
        return CrawlRun(
            id=record.id,
            target_url=record.target_url,
            hostname=record.hostname,
            status=RunStatus(record.status),
            score=record.score,
            score_breakdown=json.loads(record.score_breakdown),
            artifact_path=record.artifact_path,
            notes=json.loads(record.notes),
            created_at=record.created_at,
            completed_at=record.completed_at,
        )


def default_repository(
    db_url: str = "sqlite:///./crawllmer.db",
) -> SqliteCrawlRepository:
    return SqliteCrawlRepository(db_url=db_url)
