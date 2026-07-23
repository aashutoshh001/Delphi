import os

import pytest

from hypothesis_agent.config.settings import AgentConfig, ScoringSettings


def test_load_uses_bundled_defaults(monkeypatch):
    # Isolated from a local .env (loaded as a side effect of importing
    # hypothesis_agent.di.container elsewhere in the test session) — this
    # test is specifically about the packaged default.yaml, not whatever a
    # developer's machine happens to have overridden in .env.
    for key in list(os.environ):
        if key.startswith("HYPOTHESIS_AGENT__"):
            monkeypatch.delenv(key, raising=False)
    config = AgentConfig.load()
    assert config.search.max_iterations == 8
    assert config.backends.llm == "mock"


def test_env_var_overrides_yaml_default(monkeypatch):
    monkeypatch.setenv("HYPOTHESIS_AGENT__SEARCH__MAX_ITERATIONS", "3")
    config = AgentConfig.load()
    assert config.search.max_iterations == 3


def test_scoring_weights_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1.0"):
        ScoringSettings(weights={"business_value": 0.5, "novelty": 0.1})


def test_scoring_weights_default_sums_to_one():
    weights = ScoringSettings().weights
    assert abs(sum(weights.values()) - 1.0) < 1e-9
