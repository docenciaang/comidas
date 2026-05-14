from __future__ import annotations

from pathlib import Path

import yaml
from sqlmodel import Session, select

from app.models.db import ROOT_DIR
from app.models.schemas import Recipe, RecipeCreate, RecipeUpdate


class RecipeBook:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_recipes(self) -> list[Recipe]:
        return list(self.session.exec(select(Recipe).order_by(Recipe.name)).all())

    def get_recipe(self, recipe_id: int) -> Recipe | None:
        return self.session.get(Recipe, recipe_id)

    def search_recipe(self, query: str) -> list[Recipe]:
        statement = select(Recipe).where(Recipe.name.contains(query))
        return list(self.session.exec(statement).all())

    def add_recipe(self, recipe: RecipeCreate) -> Recipe:
        record = Recipe(
            name=recipe.name,
            description=recipe.description,
            ingredients="\n".join(recipe.ingredients),
            steps="\n".join(recipe.steps),
            tags=", ".join(recipe.tags),
            servings=recipe.servings,
            source_url=recipe.source_url,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def update_recipe(self, recipe_id: int, recipe: RecipeUpdate) -> Recipe | None:
        record = self.get_recipe(recipe_id)
        if record is None:
            return None
        record.name = recipe.name
        record.description = recipe.description
        record.ingredients = "\n".join(recipe.ingredients)
        record.steps = "\n".join(recipe.steps)
        record.tags = ", ".join(recipe.tags)
        record.servings = recipe.servings
        record.source_url = recipe.source_url
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def delete_recipe(self, recipe_id: int) -> bool:
        record = self.get_recipe(recipe_id)
        if record is None:
            return False
        self.session.delete(record)
        self.session.commit()
        return True

    @staticmethod
    def serialize(recipe: Recipe) -> dict:
        return {
            "id": recipe.id,
            "name": recipe.name,
            "description": recipe.description,
            "ingredients": [item for item in recipe.ingredients.splitlines() if item.strip()],
            "steps": [item for item in recipe.steps.splitlines() if item.strip()],
            "tags": [item.strip() for item in recipe.tags.split(",") if item.strip()],
            "servings": recipe.servings,
            "source_url": recipe.source_url,
        }

    def import_from_url(self, url: str) -> RecipeCreate:
        title = url.rstrip("/").split("/")[-1].replace("-", " ").title() or "Receta importada"
        return RecipeCreate(
            name=title,
            description=f"Receta importada desde {url}",
            ingredients=["1 ingrediente pendiente de revisar"],
            steps=["Revisar el contenido original y completar la receta."],
            tags=["importada"],
            source_url=url,
        )

    def export_yaml_catalog(self) -> list[Path]:
        recipes_dir = ROOT_DIR / "data" / "recipes"
        recipes_dir.mkdir(parents=True, exist_ok=True)
        exported: list[Path] = []
        for recipe in self.list_recipes():
            filename = recipes_dir / f"{recipe.name.lower().replace(' ', '_')}.yaml"
            payload = {
                "name": recipe.name,
                "description": recipe.description,
                "ingredients": [x for x in recipe.ingredients.splitlines() if x.strip()],
                "steps": [x for x in recipe.steps.splitlines() if x.strip()],
                "tags": [x.strip() for x in recipe.tags.split(",") if x.strip()],
                "servings": recipe.servings,
                "source_url": recipe.source_url,
            }
            filename.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")
            exported.append(filename)
        return exported
