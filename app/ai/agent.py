from __future__ import annotations

import json
from datetime import date

from diskcache import Cache
from sqlmodel import Session

from app.core.family import FamilyProfile
from app.core.menu_manager import DAYS, MenuManager
from app.core.recipes import RecipeBook
from app.models.db import ROOT_DIR, load_file_config, load_settings
from app.models.schemas import AIHistory, MenuSuggestion

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class AIAgentError(RuntimeError):
    pass


class AIAgent:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.recipe_book = RecipeBook(session)
        self.family = FamilyProfile(session)
        config = load_file_config()
        self.config = config.ai
        self.cache = Cache(str(ROOT_DIR / config.cache_dir))
        self.prompt_path = ROOT_DIR / "app" / "ai" / "prompts" / "menu_system_prompt.txt"
        self.settings = load_settings()

    def system_prompt(self) -> str:
        return self.prompt_path.read_text(encoding="utf-8").strip()

    def build_prompt(self, week_start: date) -> str:
        week_start = MenuManager.normalize_week_start(week_start)
        context = {
            "week_start": str(week_start),
            "family": self.family.family_context(),
            "recipes": [recipe.name for recipe in self.recipe_book.list_recipes()],
        }
        return json.dumps(context, ensure_ascii=True, sort_keys=True)

    def suggest_week_menu(self, week_start: date) -> MenuSuggestion:
        week_start = MenuManager.normalize_week_start(week_start)
        prompt = self.build_prompt(week_start)
        cache_key = f"week:{week_start.isoformat()}:{hash(prompt)}"
        if cache_key in self.cache:
            payload = self.cache[cache_key]
        else:
            payload = self._generate_menu_payload(week_start, prompt)
            self.cache[cache_key] = payload
        self._store_history(prompt, payload)
        return MenuSuggestion.model_validate(payload)

    def _generate_menu_payload(self, week_start: date, prompt: str) -> dict:
        provider = self.config.provider.strip().lower()
        if provider == "mock":
            return self._generate_mock_menu_payload(week_start)
        if provider == "openai":
            return self._generate_openai_menu_payload(prompt)
        raise AIAgentError(f"Proveedor de IA no soportado: {self.config.provider}")

    def _generate_mock_menu_payload(self, week_start: date) -> dict:
        week_start = MenuManager.normalize_week_start(week_start)
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

    def _generate_openai_menu_payload(self, prompt: str) -> dict:
        if OpenAI is None:
            raise AIAgentError("Falta la dependencia `openai`. Instala requirements.txt antes de usar provider=openai.")
        if not self.settings.openai_api_key:
            raise AIAgentError("Falta OPENAI_API_KEY para usar provider=openai.")

        client = OpenAI(api_key=self.settings.openai_api_key)
        response = client.responses.parse(
            model=self.config.model,
            temperature=self.config.temperature,
            input=[
                {"role": "system", "content": self.system_prompt()},
                {"role": "user", "content": prompt},
            ],
            text_format=MenuSuggestion,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise AIAgentError("OpenAI no devolvio una sugerencia estructurada valida.")
        return parsed.model_dump(mode="json")

    def _store_history(self, prompt: str, payload: dict) -> None:
        entry = AIHistory(
            prompt=prompt,
            response=json.dumps(payload, ensure_ascii=True),
            provider=self.config.provider,
            model=self.config.model,
        )
        self.session.add(entry)
        self.session.commit()
