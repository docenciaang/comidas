from __future__ import annotations

from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.staticfiles import StaticFiles

from app.ai.agent import AIAgent, AIAgentError
from app.ai.assistant import FamilyAssistant
from app.core.family import FamilyProfile
from app.core.menu_manager import MenuManager
from app.core.recipes import RecipeBook
from app.core.shopping import ShoppingList
from app.models.db import ROOT_DIR, get_session, init_db
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    FamilyMemberCreate,
    FamilyMemberUpdate,
    MenuSuggestion,
    RecipeCreate,
    RecipeUpdate,
)
from app.services.auth import require_auth
from app.web.router import router as web_router


app = FastAPI(title="Gestor de Menus Familiares", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "app" / "web" / "static")), name="static")
app.include_router(web_router)


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    with get_session() as session:
        MenuManager(session).normalize_stored_week_starts()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/menus/week", dependencies=[Depends(require_auth)])
def get_week_menu(week_start: date | None = None) -> dict:
    with get_session() as session:
        manager = MenuManager(session)
        selected_week = manager.normalize_week_start(week_start) if week_start else manager.get_current_week_start()
        items = manager.list_week_menu(week_start)
        return {
            "week_start": str(selected_week),
            "items": [manager.serialize_entry(entry) for entry in items],
        }


@app.post("/menus/week", dependencies=[Depends(require_auth)])
def save_week_menu(payload: MenuSuggestion) -> dict:
    with get_session() as session:
        saved = MenuManager(session).save_week_menu(payload)
        return {"saved_items": len(saved)}


@app.put("/menus/week", dependencies=[Depends(require_auth)])
def update_week_menu(payload: MenuSuggestion) -> dict:
    with get_session() as session:
        saved = MenuManager(session).save_week_menu(payload)
        return {"saved_items": len(saved)}


@app.delete("/menus/week", dependencies=[Depends(require_auth)])
def delete_week_menu(week_start: date) -> dict:
    with get_session() as session:
        manager = MenuManager(session)
        normalized_week_start = manager.normalize_week_start(week_start)
        deleted = manager.delete_week_menu(normalized_week_start)
        if deleted == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe menu para esa semana")
        return {"deleted_items": deleted, "week_start": normalized_week_start.isoformat()}


@app.post("/suggest", dependencies=[Depends(require_auth)])
def suggest_week_menu(week_start: date | None = None) -> dict:
    with get_session() as session:
        manager = MenuManager(session)
        start = manager.normalize_week_start(week_start) if week_start else manager.get_current_week_start()
        try:
            suggestion = AIAgent(session).suggest_week_menu(start)
        except AIAgentError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
        return suggestion.model_dump()


@app.get("/shopping-list", dependencies=[Depends(require_auth)])
def shopping_list() -> dict:
    with get_session() as session:
        return {"items": ShoppingList(session).generate()}


@app.get("/recipes", dependencies=[Depends(require_auth)])
def list_recipes() -> dict:
    with get_session() as session:
        book = RecipeBook(session)
        return {"items": [book.serialize(recipe) for recipe in book.list_recipes()]}


@app.get("/recipes/{recipe_id}", dependencies=[Depends(require_auth)])
def get_recipe(recipe_id: int) -> dict:
    with get_session() as session:
        book = RecipeBook(session)
        recipe = book.get_recipe(recipe_id)
        if recipe is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
        return book.serialize(recipe)


@app.post("/recipes", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_auth)])
def create_recipe(payload: RecipeCreate) -> dict:
    with get_session() as session:
        book = RecipeBook(session)
        record = book.add_recipe(payload)
        return book.serialize(record)


@app.put("/recipes/{recipe_id}", dependencies=[Depends(require_auth)])
def update_recipe(recipe_id: int, payload: RecipeUpdate) -> dict:
    with get_session() as session:
        book = RecipeBook(session)
        record = book.update_recipe(recipe_id, payload)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
        return book.serialize(record)


@app.delete("/recipes/{recipe_id}", dependencies=[Depends(require_auth)])
def delete_recipe(recipe_id: int) -> Response:
    with get_session() as session:
        deleted = RecipeBook(session).delete_recipe(recipe_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/family", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_auth)])
def create_family_member(payload: FamilyMemberCreate) -> dict:
    with get_session() as session:
        family = FamilyProfile(session)
        record = family.add_member(payload)
        return family.serialize(record)


@app.get("/family", dependencies=[Depends(require_auth)])
def get_family() -> dict:
    with get_session() as session:
        family = FamilyProfile(session)
        return {
            "summary": family.family_context(),
            "members": [family.serialize(member) for member in family.list_members()],
        }


@app.get("/family/{member_id}", dependencies=[Depends(require_auth)])
def get_family_member(member_id: int) -> dict:
    with get_session() as session:
        family = FamilyProfile(session)
        member = family.get_member(member_id)
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")
        return family.serialize(member)


@app.put("/family/{member_id}", dependencies=[Depends(require_auth)])
def update_family_member(member_id: int, payload: FamilyMemberUpdate) -> dict:
    with get_session() as session:
        family = FamilyProfile(session)
        member = family.update_member(member_id, payload)
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")
        return family.serialize(member)


@app.delete("/family/{member_id}", dependencies=[Depends(require_auth)])
def delete_family_member(member_id: int) -> Response:
    with get_session() as session:
        deleted = FamilyProfile(session).delete_member(member_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/assistant", response_model=ChatResponse, dependencies=[Depends(require_auth)])
def assistant_chat(payload: ChatRequest) -> ChatResponse:
    with get_session() as session:
        answer = FamilyAssistant(session).answer(payload.message)
        return ChatResponse(answer=answer)


@app.post("/init-db", dependencies=[Depends(require_auth)])
def initialize_db() -> Response:
    init_db()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
