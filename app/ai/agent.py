from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from diskcache import Cache
from sqlmodel import Session

from app.core.family import FamilyProfile
from app.core.menu_manager import DAYS
from app.core.recipes import RecipeBook
from app.models.db import ROOT_DIR, load_file_config
from app.models.schemas import AIHistory, MenuSuggestion, MenuSuggestionItem


class AIAgent:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.recipe_book = RecipeBook(session)
        self.family = FamilyProfile(session)
        config = load_file_config()
        self.config = config.ai
        self.cache = Cache(str(ROOT_DIR / config.cache_dir))
        self.prompt_path = ROOT_DIR / "app" / "ai" / "prompts" / "menu_system_prompt.txt"

    def build_prompt(self, week_start: date) -> str:
        context = {
            "week_start": str(week_start),
            "family": self.family.family_context(),
            "recipes": [recipe.name for recipe in self.recipe_book.list_recipes()],
            "system_prompt": self.prompt_path.read_text(encoding="utf-8").strip(),
        }
        return json.dumps(context, ensure_ascii=True, sort_keys=True)

    def suggest_week_menu(self, week_start: date) -> MenuSuggestion:
        prompt = self.build_prompt(week_start)
        cache_key = f"week:{week_start.isoformat()}:{hash(prompt)}"
        if cache_key in self.cache:
            payload = self.cache[cache_key]
        else:
            payload = self._generate_menu_payload(week_start)
            self.cache[cache_key] = payload
        self._store_history(prompt, payload)
        return MenuSuggestion.model_validate(payload)

    def _generate_menu_payload(self, week_start: date) -> dict:
        recipes = self.recipe_book.list_recipes()
        recipe_names = [recipe.name for recipe in recipes] or ["Pasta con verduras", "Crema de calabaza", "Tortilla francesa"]
        items = []
        for index, day in enumerate(DAYS):
            recipe_name = recipe_names[index % len(recipe_names)]
            items.append(
                {
                    "day": day,
                    "meal_type": "comida",
                    "recipe_name": recipe_name,
                    "servings": max(self.family.family_context().get("count", 0), 1),
                    "notes": "Sugerencia generada en modo mock",
                }
            )
        return {"week_start": str(week_start), "items": items}

    def _store_history(self, prompt: str, payload: dict) -> None:
        entry = AIHistory(
            prompt=prompt,
            response=json.dumps(payload, ensure_ascii=True),
            provider=self.config.provider,
            model=self.config.model,
        )
        self.session.add(entry)
        self.session.commit()
