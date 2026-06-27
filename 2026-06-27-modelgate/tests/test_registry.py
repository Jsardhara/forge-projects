"""Tests for ModelGate registry defaults."""

from modelgate.models import ModelTier
from modelgate.registry import DEFAULT_MODELS


class TestDefaultModels:
    def test_models_exist(self):
        assert len(DEFAULT_MODELS) >= 10

    def test_each_tier_represented(self):
        tiers = {m.tier for m in DEFAULT_MODELS}
        assert ModelTier.PUBLIC in tiers
        assert ModelTier.RESTRICTED in tiers
        assert ModelTier.CLASSIFIED in tiers
        assert ModelTier.GOVERNMENT_VETTED in tiers

    def test_gpt56_is_classified(self):
        gpt56 = [m for m in DEFAULT_MODELS if m.name == "gpt-5.6"]
        assert len(gpt56) == 1
        assert gpt56[0].tier == ModelTier.CLASSIFIED

    def test_mythos_is_classified(self):
        mythos = [m for m in DEFAULT_MODELS if m.name == "mythos"]
        assert len(mythos) == 1
        assert mythos[0].tier == ModelTier.CLASSIFIED

    def test_no_duplicate_names(self):
        names = [m.name for m in DEFAULT_MODELS]
        assert len(names) == len(set(names))

    def test_all_have_provider(self):
        for m in DEFAULT_MODELS:
            assert m.provider, f"Model {m.name} missing provider"
