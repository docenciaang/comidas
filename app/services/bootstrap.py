from __future__ import annotations

from sqlmodel import Session

from app.core.family import FamilyProfile
from app.core.recipes import RecipeBook
from app.models.schemas import FamilyMemberCreate, RecipeCreate


def seed_demo_data(session: Session) -> None:
    family = FamilyProfile(session)
    recipes = RecipeBook(session)
    if not family.list_members():
        family.add_member(
            FamilyMemberCreate(
                name="Ana",
                age=38,
                allergies=["marisco"],
                preferences=["verduras"],
                restrictions=["sin picante"],
            )
        )
        family.add_member(FamilyMemberCreate(name="Leo", age=10, preferences=["pasta"]))
    if not recipes.list_recipes():
        recipes.add_recipe(
            RecipeCreate(
                name="Lentejas estofadas",
                description="Plato de cuchara familiar",
                ingredients=["lentejas", "zanahoria", "cebolla"],
                steps=["Sofreir verduras", "Cocer lentejas"],
                tags=["casera", "legumbres"],
                servings=4,
            )
        )
        recipes.add_recipe(
            RecipeCreate(
                name="Arroz con pollo",
                description="Clasico semanal",
                ingredients=["arroz", "pollo", "pimiento"],
                steps=["Dorar pollo", "Cocer arroz"],
                tags=["rapida"],
                servings=4,
            )
        )
