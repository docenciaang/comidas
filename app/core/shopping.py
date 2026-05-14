from __future__ import annotations

from collections import Counter
from pathlib import Path

from sqlmodel import Session

from app.core.menu_manager import MenuManager
from app.core.recipes import RecipeBook
from app.models.db import ROOT_DIR


class ShoppingList:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.menu_manager = MenuManager(session)
        self.recipe_book = RecipeBook(session)

    def generate(self) -> list[str]:
        recipe_map = {recipe.name: recipe for recipe in self.recipe_book.list_recipes()}
        counts: Counter[str] = Counter()
        for entry in self.menu_manager.list_week_menu():
            recipe = recipe_map.get(entry.recipe_name)
            if not recipe:
                continue
            for ingredient in recipe.ingredients.splitlines():
                if ingredient.strip():
                    counts[ingredient.strip()] += 1
        return [f"{ingredient} x{amount}" for ingredient, amount in sorted(counts.items())]

    def export_text(self) -> Path:
        output = ROOT_DIR / "data" / "shopping_list.txt"
        output.write_text("\n".join(self.generate()) or "Sin items pendientes", encoding="utf-8")
        return output
