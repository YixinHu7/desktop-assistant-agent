import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from typing import Literal
from openai import OpenAI

from app.config import config


@dataclass
class Skill:
    name: str
    description: str
    path: str
    instructions: str


class SkillRegistry:
    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills = self._load_skills()

    def _load_skills(self) -> List[Skill]:
        if not self.skills_dir.exists():
            return []

        loaded = []

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"

            if not skill_file.exists():
                continue

            raw = skill_file.read_text(encoding="utf-8")
            name, description, body = self._parse_skill_md(raw)

            if name and description:
                loaded.append(
                    Skill(
                        name=name,
                        description=description,
                        path=str(skill_file),
                        instructions=body.strip(),
                    )
                )

        return loaded

    def _parse_skill_md(self, raw: str):
        frontmatter_match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.DOTALL)

        if not frontmatter_match:
            return None, None, raw

        frontmatter = frontmatter_match.group(1)
        body = frontmatter_match.group(2)

        name = None
        description = None

        for line in frontmatter.splitlines():
            if line.startswith("name:"):
                name = line.replace("name:", "", 1).strip()
            elif line.startswith("description:"):
                description = line.replace("description:", "", 1).strip()

        return name, description, body

    def list_skill_summaries(self):
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "path": skill.path,
            }
            for skill in self.skills
        ]

    def get_skill(self, name: str) -> Optional[Skill]:
        for skill in self.skills:
            if skill.name == name:
                return skill
        return None



class SkillDecision(BaseModel):
    selected_skill: Optional[str] = None
    should_use_skill: bool
    reason: str


class SkillSelector:
    def __init__(self, client: OpenAI, registry: SkillRegistry):
        self.client = client
        self.registry = registry

    def decide(self, user_input: str) -> SkillDecision:
        skills = self.registry.list_skill_summaries()

        if not skills:
            return SkillDecision(
                selected_skill=None,
                should_use_skill=False,
                reason="No skills are available."
            )

        prompt = f"""
You are a skill selection module for a desktop assistant agent.

Decide whether one of the available skills should be used.

Available skills:
{skills}

Rules:
- Select a skill only when the user's request clearly matches the skill description.
- Do not select a skill for general chat or unrelated tasks.
- If no skill fits, return should_use_skill=false.

User input:
{user_input}
"""

        response = self.client.responses.parse(
            model=config.model,
            input=[
                {"role": "system", "content": "Return a structured skill decision."},
                {"role": "user", "content": prompt},
            ],
            text_format=SkillDecision,
        )

        decision = response.output_parsed

        if decision.should_use_skill and decision.selected_skill:
            if self.registry.get_skill(decision.selected_skill) is None:
                return SkillDecision(
                    selected_skill=None,
                    should_use_skill=False,
                    reason=f"Selected skill {decision.selected_skill} does not exist."
                )

        return decision