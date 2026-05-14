from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class MealType(str, Enum):
    COMIDA = "comida"
    CENA = "cena"


class FamilyMember(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    age: int
    allergies: str = ""
    preferences: str = ""
    restrictions: str = ""
    meals_per_day: int = 2


class Recipe(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str = ""
    ingredients: str
    steps: str = ""
    tags: str = ""
    servings: int = 4
    source_url: str = ""


class MenuEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    week_start: date = Field(index=True)
    day: str = Field(index=True)
    meal_type: str = MealType.COMIDA.value
    recipe_name: str
    servings: int = 4
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AIHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    prompt: str
    response: str
    provider: str = "mock"
    model: str = "gpt-4.1-mini"


class RecipeCreate(BaseModel):
    name: str
    description: str = ""
    ingredients: list[str]
    steps: list[str] = []
    tags: list[str] = []
    servings: int = 4
    source_url: str = ""


class RecipeUpdate(RecipeCreate):
    pass


class FamilyMemberCreate(BaseModel):
    name: str
    age: int
    allergies: list[str] = []
    preferences: list[str] = []
    restrictions: list[str] = []
    meals_per_day: int = 2


class FamilyMemberUpdate(FamilyMemberCreate):
    pass


class MenuSuggestionItem(BaseModel):
    day: str
    meal_type: MealType = MealType.COMIDA
    recipe_name: str
    servings: int
    notes: str = ""


class MenuSuggestion(BaseModel):
    week_start: date
    items: list[MenuSuggestionItem]


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
