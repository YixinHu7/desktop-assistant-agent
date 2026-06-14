import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional, Tuple

from openai import OpenAI
from pydantic import BaseModel, Field

from app.config import config


@dataclass
class Skill:
    name: str
    description: str
    path: str
    instructions: str
    triggers: List[str]


class SkillRegistry:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills = self._load_skills()

    def _load_skills(self) -> List[Skill]:
        if not self.skills_dir.exists():
            return []

        loaded: List[Skill] = []

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"

            if not skill_file.exists():
                continue

            raw = skill_file.read_text(encoding="utf-8")
            name, description, triggers, body = self._parse_skill_md(raw)

            if not name or not description:
                continue

            loaded.append(
                Skill(
                    name=name,
                    description=description,
                    path=str(skill_file),
                    instructions=body.strip(),
                    triggers=triggers,
                )
            )

        return loaded

    def _parse_skill_md(
        self,
        raw: str,
    ) -> Tuple[
        Optional[str],
        Optional[str],
        List[str],
        str,
    ]:
        frontmatter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$",
            raw,
            re.DOTALL,
        )

        if not frontmatter_match:
            return None, None, [], raw

        frontmatter = frontmatter_match.group(1)
        body = frontmatter_match.group(2)

        name: Optional[str] = None
        description: Optional[str] = None
        triggers: List[str] = []

        for line in frontmatter.splitlines():
            key, separator, value = line.partition(":")

            if not separator:
                continue

            key = key.strip()
            value = value.strip()

            if key == "name":
                name = value
            elif key == "description":
                description = value
            elif key == "triggers":
                triggers = [
                    trigger.strip()
                    for trigger in value.split(",")
                    if trigger.strip()
                ]

        return name, description, triggers, body

    def list_skill_summaries(self) -> List[dict]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "triggers": skill.triggers,
                "path": skill.path,
            }
            for skill in self.skills
        ]

    def get_skill(self, name: str) -> Optional[Skill]:
        for skill in self.skills:
            if skill.name == name:
                return skill

        return None

    def find_candidates(
        self,
        user_input: str,
        max_candidates: int = 3,
    ) -> List[dict]:
        text = user_input.lower()
        candidates = []

        for skill in self.skills:
            matched_triggers = [
                trigger
                for trigger in skill.triggers
                if trigger.lower() in text
            ]

            if not matched_triggers:
                continue

            candidates.append(
                {
                    "name": skill.name,
                    "description": skill.description,
                    "score": len(matched_triggers),
                    "matched_triggers": matched_triggers,
                }
            )

        candidates.sort(
            key=lambda candidate: (
                -candidate["score"],
                candidate["name"],
            )
        )

        return candidates[:max_candidates]


class ModelSkillDecision(BaseModel):
    selected_skill: Optional[str] = None
    should_use_skill: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class SkillDecision(BaseModel):
    selected_skill: Optional[str] = None
    should_use_skill: bool
    confidence: float = Field(ge=0.0, le=1.0)
    selection_method: Literal["none", "rule", "model"]
    candidate_skills: List[str] = Field(default_factory=list)
    reason: str


class SkillSelector:
    def __init__(
        self,
        client: OpenAI,
        registry: SkillRegistry,
    ):
        self.client = client
        self.registry = registry

    def decide(self, user_input: str) -> SkillDecision:
        candidates = self.registry.find_candidates(user_input)
        candidate_names = [
            candidate["name"]
            for candidate in candidates
        ]

        # No lexical candidate means no skill and no model call.
        if not candidates:
            return SkillDecision(
                selected_skill=None,
                should_use_skill=False,
                confidence=1.0,
                selection_method="none",
                candidate_skills=[],
                reason="No skill trigger matched the user request.",
            )

        strongest_candidate = candidates[0]

        # Strong deterministic match avoids an unnecessary model call.
        if (
            len(candidates) == 1
            and strongest_candidate["score"]
            >= config.skill_rule_min_matches
        ):
            return SkillDecision(
                selected_skill=strongest_candidate["name"],
                should_use_skill=True,
                confidence=1.0,
                selection_method="rule",
                candidate_skills=candidate_names,
                reason=(
                    "The request strongly matched multiple triggers "
                    f"for {strongest_candidate['name']}."
                ),
            )

        prompt = f"""
You are a skill selection module for a desktop assistant agent.

Choose whether one of the candidate skills should be used.

Candidate skills:
{candidates}

Rules:
- Select only from the candidate skill names.
- Select a skill only when it materially improves how the request is handled.
- Do not select a skill merely because one keyword appears.
- Do not select a skill for general chat or unrelated requests.
- Return should_use_skill=false when no candidate is a clear fit.
- Confidence must reflect how clearly the request matches the selected skill.

User input:
{user_input}
"""

        response = self.client.responses.parse(
            model=config.model,
            input=[
                {
                    "role": "system",
                    "content": "Return a structured skill decision.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            text_format=ModelSkillDecision,
        )

        model_decision = response.output_parsed

        if (
            not model_decision.should_use_skill
            or not model_decision.selected_skill
        ):
            return SkillDecision(
                selected_skill=None,
                should_use_skill=False,
                confidence=model_decision.confidence,
                selection_method="model",
                candidate_skills=candidate_names,
                reason=model_decision.reason,
            )

        # Reject skills that were not part of the candidate shortlist.
        if model_decision.selected_skill not in candidate_names:
            return SkillDecision(
                selected_skill=None,
                should_use_skill=False,
                confidence=0.0,
                selection_method="model",
                candidate_skills=candidate_names,
                reason=(
                    "The model selected a skill that was not in "
                    "the candidate shortlist."
                ),
            )

        # Reject low-confidence selections.
        if (
            model_decision.confidence
            < config.skill_selection_threshold
        ):
            return SkillDecision(
                selected_skill=None,
                should_use_skill=False,
                confidence=model_decision.confidence,
                selection_method="model",
                candidate_skills=candidate_names,
                reason=(
                    f"Skill confidence {model_decision.confidence:.2f} "
                    f"was below the configured threshold "
                    f"{config.skill_selection_threshold:.2f}. "
                    f"{model_decision.reason}"
                ),
            )

        return SkillDecision(
            selected_skill=model_decision.selected_skill,
            should_use_skill=True,
            confidence=model_decision.confidence,
            selection_method="model",
            candidate_skills=candidate_names,
            reason=model_decision.reason,
        )