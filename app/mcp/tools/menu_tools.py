from __future__ import annotations

from sqlmodel import Session

from app.core.family import FamilyProfile
from app.core.recipes import RecipeBook
from app.core.shopping import ShoppingList


def search_recipe(session: Session, query: str) -> list[str]:
    return [recipe.name for recipe in RecipeBook(session).search_recipe(query)]


def list_available_ingredients(session: Session) -> list[str]:
    ingredients: set[str] = set()
    for recipe in RecipeBook(session).list_recipes():
        ingredients.update({item.strip() for item in recipe.ingredients.splitlines() if item.strip()})
    return sorted(ingredients)


def get_nutrition_info(session: Session, dish: str) -> dict:
    recipes = RecipeBook(session).search_recipe(dish)
    if not recipes:
        return {"dish": dish, "status": "not_found"}
    ingredient_count = len([item for item in recipes[0].ingredients.splitlines() if item.strip()])
    return {"dish": recipes[0].name, "status": "estimated", "ingredient_count": ingredient_count}


def generate_shopping_list(session: Session) -> list[str]:
    return ShoppingList(session).generate()


def get_family_profile(session: Session) -> dict:
    return FamilyProfile(session).family_context()
