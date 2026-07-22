from hypothesis_agent.contracts.memory import FeedbackSummary
from hypothesis_agent.plugins.memory_policies.soft_prior_policy import SoftPriorPolicy


def test_empty_feedback_yields_no_priors():
    policy = SoftPriorPolicy()
    assert policy.compute_lens_priors({}) == {}


def test_balanced_feedback_yields_prior_near_one():
    policy = SoftPriorPolicy(min_multiplier=0.7, max_multiplier=1.3)
    priors = policy.compute_lens_priors({"a": FeedbackSummary(up_count=5, down_count=5)})
    assert abs(priors["a"] - 1.0) < 1e-9


def test_lopsided_feedback_stays_within_bounds():
    policy = SoftPriorPolicy(min_multiplier=0.7, max_multiplier=1.3)
    all_up = policy.compute_lens_priors({"a": FeedbackSummary(up_count=100, down_count=0)})
    all_down = policy.compute_lens_priors({"a": FeedbackSummary(up_count=0, down_count=100)})
    assert 0.7 <= all_down["a"] < 1.0 < all_up["a"] <= 1.3


def test_single_vote_barely_moves_the_prior():
    policy = SoftPriorPolicy(min_multiplier=0.7, max_multiplier=1.3, smoothing=3.0)
    priors = policy.compute_lens_priors({"a": FeedbackSummary(up_count=1, down_count=0)})
    assert 0.95 < priors["a"] < 1.1
