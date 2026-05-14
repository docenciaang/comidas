from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.ai.agent import AIAgent
from app.core.menu_manager import MenuManager
from app.mcp.resources.catalog import collect_resources
from app.mcp.tools.menu_tools import (
    generate_shopping_list,
    get_family_profile,
    get_nutrition_info,
    list_available_ingredients,
    search_recipe,
)
from app.models.db import get_session


@dataclass
class MCPServerLocal:
    name: str = "menu-familiar-mcp"

    def get_menu_week(self) -> dict:
        with get_session() as session:
            return {
                day: [entry.recipe_name for entry in entries]
                for day, entries in MenuManager(session).as_week_table().items()
            }

    def get_family_profile(self) -> dict:
        with get_session() as session:
            return get_family_profile(session)

    def save_suggested_menu(self, week_start: date) -> dict:
        with get_session() as session:
            suggestion = AIAgent(session).suggest_week_menu(week_start)
            saved = MenuManager(session).save_week_menu(suggestion)
            return {"saved_items": len(saved), "week_start": str(week_start)}

    def tools(self) -> dict:
        with get_session() as session:
            return {
                "search_recipe": lambda query: search_recipe(session, query),
                "list_available_ingredients": lambda: list_available_ingredients(session),
                "get_nutrition_info": lambda dish: get_nutrition_info(session, dish),
                "generate_shopping_list": lambda: generate_shopping_list(session),
            }

    def resources(self) -> dict:
        with get_session() as session:
            return collect_resources(session)
