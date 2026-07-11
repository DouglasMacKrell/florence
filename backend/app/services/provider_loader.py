import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.tables import ProviderRecordORM
from app.models.provider import ProviderRecord


def load_providers_from_seed(session: Session) -> int:
    if session.query(ProviderRecordORM).count() > 0:
        return 0

    seed_path = Path(__file__).resolve().parents[3] / "data" / "providers.json"
    providers = json.loads(seed_path.read_text())
    for entry in providers:
        provider = ProviderRecord.model_validate(entry)
        session.add(
            ProviderRecordORM(
                id=provider.id,
                name=provider.name,
                provider_type=provider.provider_type,
                payload_json=provider.model_dump(),
            )
        )
    session.flush()
    return len(providers)


def list_provider_records(session: Session) -> list[ProviderRecord]:
    rows = session.query(ProviderRecordORM).all()
    return [ProviderRecord.model_validate(row.payload_json) for row in rows]
