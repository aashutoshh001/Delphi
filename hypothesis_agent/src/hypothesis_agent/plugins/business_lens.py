"""Built-in business lens catalog. Each lens is a thematic direction the
search heuristic diversifies over — adding a new one is a `register()` call,
never a code change elsewhere."""

from __future__ import annotations

from hypothesis_agent.contracts.hypothesis import BusinessLens
from hypothesis_agent.plugins.registry import PluginRegistry

_BUILTIN_LENSES: list[BusinessLens] = [
    BusinessLens(
        id="burnout_resilience",
        display_name="Burnout & Resilience",
        description="How performance, workload, and resilience/burnout signals interact.",
        seed_questions=[
            "Are the highest performers also the most burned out?",
            "Does resilience protect high performers from exhaustion?",
        ],
        relevant_construct_categories=["performance", "burnout", "resilience", "engagement"],
    ),
    BusinessLens(
        id="skill_concentration",
        display_name="Critical Skill Concentration",
        description="Whether critical competencies are dangerously concentrated in a few people.",
        seed_questions=[
            "Are business-critical technical competencies concentrated in a small subset of employees?",
            "What single-point-of-failure risk exists in scarce skill areas?",
        ],
        relevant_construct_categories=["technical_competency", "tenure", "role_criticality"],
    ),
    BusinessLens(
        id="promotion_equity",
        display_name="Promotion & Merit Alignment",
        description="Whether advancement tracks the competencies the org claims to value.",
        seed_questions=[
            "Is technical excellence alone insufficient for promotion?",
            "Do behavioural competencies predict promotion better than technical ones?",
        ],
        relevant_construct_categories=["promotion", "technical_competency", "behavioural_competency"],
    ),
    BusinessLens(
        id="leadership_influence",
        display_name="Leadership's Indirect Effects",
        description="Second-order effects of leadership quality on outcomes it doesn't directly control.",
        seed_questions=[
            "Do leadership competencies indirectly reduce attrition through team-level effects?",
            "Does manager quality moderate the effect of workload on engagement?",
        ],
        relevant_construct_categories=["leadership", "manager_ratings", "attrition", "engagement"],
    ),
    BusinessLens(
        id="communication_protection",
        display_name="Communication as a Protective Factor",
        description="Whether communication/collaboration competencies buffer negative outcomes.",
        seed_questions=[
            "Do strong communication competencies protect against organizational exhaustion?",
            "Does collaboration skill offset low tenure in predicting performance?",
        ],
        relevant_construct_categories=["communication", "collaboration", "burnout", "performance"],
    ),
    BusinessLens(
        id="attrition_hidden_drivers",
        display_name="Hidden Attrition Drivers",
        description="Non-obvious, indirect predictors of attrition beyond compensation.",
        seed_questions=[
            "Is attrition risk better predicted by growth stagnation than by pay?",
            "Do adaptability scores predict attrition under organizational change?",
        ],
        relevant_construct_categories=["attrition", "tenure", "learning", "adaptability"],
    ),
    BusinessLens(
        id="learning_velocity",
        display_name="Learning Velocity & Future Readiness",
        description="How fast employees build new capability relative to strategic needs.",
        seed_questions=[
            "Does learning velocity early in tenure predict long-run performance?",
            "Are the employees the org will most need to reskill the least engaged with learning?",
        ],
        relevant_construct_categories=["learning", "adaptability", "tenure", "performance"],
    ),
    BusinessLens(
        id="compensation_fairness",
        display_name="Compensation & Perceived Fairness",
        description="Where compensation structure creates hidden strategic risk, beyond raw pay gaps.",
        seed_questions=[
            "Does perceived pay fairness matter more than absolute pay for engagement?",
            "Is compensation compression concentrated among the org's highest performers?",
        ],
        relevant_construct_categories=["salary", "performance", "engagement", "tenure"],
    ),
    BusinessLens(
        id="psychometric_fit",
        display_name="Psychometric–Role Fit",
        description="Whether psychometric/behavioural profiles predict success in specific role types.",
        seed_questions=[
            "Do specific psychometric profiles predict success in ambiguous vs. structured roles?",
            "Is a mismatch between psychometric profile and role type a hidden attrition driver?",
        ],
        relevant_construct_categories=["psychometrics", "assessments", "performance", "attrition"],
    ),
    BusinessLens(
        id="network_effects",
        display_name="Informal Network & Collaboration Effects",
        description="How informal collaboration structure shapes outcomes formal hierarchy misses.",
        seed_questions=[
            "Do cross-department collaborators outperform siloed peers on innovation-linked metrics?",
            "Is organizational influence concentrated outside the formal management hierarchy?",
        ],
        relevant_construct_categories=["collaboration", "organizational_structure", "performance"],
    ),
]


def default_lens_registry() -> PluginRegistry[BusinessLens]:
    registry: PluginRegistry[BusinessLens] = PluginRegistry(kind="business_lens")
    for lens in _BUILTIN_LENSES:
        registry.register(lens.id, lens)
    return registry
