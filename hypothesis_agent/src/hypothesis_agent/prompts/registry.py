"""Prompt architecture: every LLM-facing prompt lives in a versioned YAML
template, loaded through this registry. Templates use `string.Template`
`$placeholder` syntax rather than f-strings/Jinja so braces inside
LLM-echoed organization data can never be misread as template syntax."""

from __future__ import annotations

from pathlib import Path
from string import Template

import yaml
from pydantic import BaseModel

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class RenderedPrompt(BaseModel):
    system: str
    user: str


class PromptTemplate(BaseModel):
    id: str
    version: str = "1"
    system: str
    user_template: str

    def render(self, **kwargs: object) -> RenderedPrompt:
        user = Template(self.user_template).safe_substitute(**kwargs)
        return RenderedPrompt(system=self.system, user=user)


class PromptRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, dict[str, PromptTemplate]] = {}

    def register(self, template: PromptTemplate, *, override: bool = False) -> None:
        versions = self._templates.setdefault(template.id, {})
        if not override and template.version in versions:
            raise KeyError(
                f"prompt '{template.id}' version '{template.version}' already registered"
            )
        versions[template.version] = template

    def get(self, prompt_id: str, version: str = "latest") -> PromptTemplate:
        versions = self._templates.get(prompt_id)
        if not versions:
            raise KeyError(f"no prompt template registered under id '{prompt_id}'")
        if version == "latest":
            return versions[max(versions, key=lambda v: [int(p) for p in v.split(".")])]
        try:
            return versions[version]
        except KeyError as exc:
            raise KeyError(
                f"prompt '{prompt_id}' has no version '{version}'; available: {sorted(versions)}"
            ) from exc

    @classmethod
    def load_from_directory(cls, directory: Path = _TEMPLATES_DIR) -> "PromptRegistry":
        registry = cls()
        for path in sorted(directory.glob("*.yaml")):
            data = yaml.safe_load(path.read_text())
            registry.register(PromptTemplate.model_validate(data))
        return registry


def default_prompt_registry() -> PromptRegistry:
    return PromptRegistry.load_from_directory()
