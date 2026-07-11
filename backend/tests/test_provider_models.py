import json
from pathlib import Path

from app.models.provider import ProviderRecord


def test_provider_record_parses_seed_entry() -> None:
    seed_path = Path(__file__).resolve().parents[2] / "data" / "providers.json"
    providers = json.loads(seed_path.read_text())
    provider = ProviderRecord.model_validate(providers[0])
    assert provider.id
    assert provider.name
    assert provider.pricing.monthly_min >= 0


def test_provider_seed_has_minimum_variety() -> None:
    seed_path = Path(__file__).resolve().parents[2] / "data" / "providers.json"
    providers = [ProviderRecord.model_validate(p) for p in json.loads(seed_path.read_text())]
    types = {p.provider_type for p in providers}
    assert len(providers) >= 15
    assert "home_care" in types
    assert "assisted_living" in types
    assert "memory_care" in types
    assert "skilled_nursing" in types
    assert "hospice" in types
