from __future__ import annotations

from sqlmodel import Session

from app.core.family import FamilyProfile
from app.core.menu_manager import MenuManager
from app.core.recipes import RecipeBook
from app.mcp.tools.menu_tools import list_available_ingredients


def collect_resources(session: Session) -> dict:
    return {
        "recipe_book": [recipe.name for recipe in RecipeBook(session).list_recipes()],
        "family_profile": FamilyProfile(session).family_context(),
        "current_week_menu": {
            day: [entry.recipe_name for entry in entries]
            for day, entries in MenuManager(session).as_week_table().items()
        },
        "pantry_inventory": list_available_ingredients(session),
    }
