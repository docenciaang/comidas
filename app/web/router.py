from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.ai.agent import AIAgent
from app.ai.assistant import FamilyAssistant
from app.core.family import FamilyProfile
from app.core.menu_manager import DAYS, MenuManager
from app.core.recipes import RecipeBook
from app.core.shopping import ShoppingList
from app.mcp.server import MCPServerLocal
from app.models.db import ROOT_DIR, get_session, init_db, load_file_config
from app.models.schemas import FamilyMemberCreate, MealType, MenuSuggestion, MenuSuggestionItem, RecipeCreate
from app.services.auth import require_auth
from app.services.bootstrap import seed_demo_data


templates = Jinja2Templates(directory=str(ROOT_DIR / "app" / "web" / "templates"))
router = APIRouter(include_in_schema=False)
MENU_SLOTS_PER_DAY = 3
MEAL_TYPE_OPTIONS = [MealType.COMIDA.value, MealType.CENA.value]
MONTH_NAMES = [
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def _split_lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _split_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _join_lines(raw: str) -> str:
    return "\n".join(line.strip() for line in raw.splitlines() if line.strip())


def _join_csv(raw: str) -> str:
    return ", ".join(item.strip() for item in raw.split(",") if item.strip())


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


def _base_context(request: Request, title: str, active: str) -> dict:
    config = load_file_config()
    return {
        "request": request,
        "title": title,
        "active": active,
        "app_name": config.app_name,
        "ai_provider": config.ai.provider,
    }


def _menu_day_rows(entries: list, slots: int = MENU_SLOTS_PER_DAY) -> list[dict]:
    rows = [
        {
            "recipe_name": entry.recipe_name,
            "meal_type": entry.meal_type,
            "servings": entry.servings,
            "notes": entry.notes,
        }
        for entry in entries
    ]
    while len(rows) < slots:
        rows.append({"recipe_name": "", "meal_type": MealType.COMIDA.value, "servings": 4, "notes": ""})
    return rows


def _week_start_for(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _shift_month(month_value: str, offset: int) -> str:
    year, month = map(int, month_value.split("-"))
    month += offset
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return f"{year:04d}-{month:02d}"


def _resolve_month(selected_week: date, month_value: str | None) -> str:
    if month_value:
        return month_value
    return selected_week.strftime("%Y-%m")


def _build_month_calendar(menu_manager: MenuManager, month_value: str, selected_week: date) -> dict:
    year, month = map(int, month_value.split("-"))
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    grid_start = _week_start_for(first_day)
    grid_end = _week_start_for(last_day) + timedelta(days=6)
    saved_weeks = set(menu_manager.list_saved_week_starts(grid_start, grid_end))
    today = date.today()
    weeks: list[list[dict]] = []
    current = grid_start
    while current <= grid_end:
        week_days: list[dict] = []
        week_start = _week_start_for(current)
        for offset in range(7):
            day = current + timedelta(days=offset)
            week_days.append(
                {
                    "date": day,
                    "day_number": day.day,
                    "in_month": day.month == month,
                    "is_today": day == today,
                    "is_selected_week": week_start == selected_week,
                    "week_start": week_start.isoformat(),
                    "has_menu": week_start in saved_weeks,
                }
            )
        weeks.append(week_days)
        current += timedelta(days=7)
    return {
        "month_value": month_value,
        "month_label": f"{MONTH_NAMES[month]} {year}",
        "prev_month": _shift_month(month_value, -1),
        "next_month": _shift_month(month_value, 1),
        "weeks": weeks,
        "selected_week": selected_week.isoformat(),
    }


@router.get("/", response_class=HTMLResponse)
def root() -> RedirectResponse:
    return _redirect("/web")


@router.get("/web", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def dashboard(request: Request, notice: str | None = None) -> HTMLResponse:
    with get_session() as session:
        menu_manager = MenuManager(session)
        week_start = menu_manager.get_current_week_start()
        week_table = menu_manager.as_week_table(week_start)
        month_calendar = _build_month_calendar(menu_manager, week_start.strftime("%Y-%m"), week_start)
        recipes = RecipeBook(session).list_recipes()
        family_members = FamilyProfile(session).list_members()
        shopping_items = ShoppingList(session).generate()
        today_name = DAYS[date.today().weekday()]
        today_items = week_table.get(today_name, [])
        context = _base_context(request, "Panel", "dashboard")
        context.update(
            {
                "notice": notice,
                "week_start": week_start.isoformat(),
                "recipe_count": len(recipes),
                "family_count": len(family_members),
                "shopping_count": len(shopping_items),
                "today_name": today_name,
                "today_items": today_items,
                "week_days": [(day, week_table.get(day, [])) for day in DAYS],
                "month_calendar": month_calendar,
            }
        )
    return templates.TemplateResponse("dashboard.html", context)


@router.get("/web/menu", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def menu_page(request: Request, week_start: str | None = None, month: str | None = None, notice: str | None = None) -> HTMLResponse:
    selected_week = date.fromisoformat(week_start) if week_start else None
    with get_session() as session:
        menu_manager = MenuManager(session)
        current_week = selected_week or menu_manager.get_current_week_start()
        week_table = menu_manager.as_week_table(current_week)
        month_value = _resolve_month(current_week, month)
        month_calendar = _build_month_calendar(menu_manager, month_value, current_week)
        recipes = RecipeBook(session).list_recipes()
        context = _base_context(request, "Menu semanal", "menu")
        context.update(
            {
                "notice": notice,
                "week_start": current_week.isoformat(),
                "week_end": (current_week + timedelta(days=6)).isoformat(),
                "recipes": recipes,
                "week_days": [(day, week_table.get(day, [])) for day in DAYS],
                "menu_rows": [(day, _menu_day_rows(week_table.get(day, []))) for day in DAYS],
                "menu_slots_per_day": MENU_SLOTS_PER_DAY,
                "meal_type_options": MEAL_TYPE_OPTIONS,
                "month_calendar": month_calendar,
                "prev_week": (current_week - timedelta(days=7)).isoformat(),
                "next_week": (current_week + timedelta(days=7)).isoformat(),
            }
        )
    return templates.TemplateResponse("menu.html", context)


@router.post("/web/menu/save", dependencies=[Depends(require_auth)])
async def save_menu(request: Request) -> RedirectResponse:
    form = await request.form()
    week_start = date.fromisoformat(str(form.get("week_start")))
    month_value = str(form.get("month") or week_start.strftime("%Y-%m"))
    items: list[MenuSuggestionItem] = []
    for day in DAYS:
        recipe_names = form.getlist(f"{day}_recipe")
        meal_types = form.getlist(f"{day}_meal_type")
        servings_list = form.getlist(f"{day}_servings")
        notes_list = form.getlist(f"{day}_notes")
        max_rows = max(len(recipe_names), len(meal_types), len(servings_list), len(notes_list))
        for index in range(max_rows):
            recipe_name = str(recipe_names[index] if index < len(recipe_names) else "").strip()
            servings_raw = str(servings_list[index] if index < len(servings_list) else "0").strip()
            notes = str(notes_list[index] if index < len(notes_list) else "").strip()
            meal_type = str(meal_types[index] if index < len(meal_types) else MealType.COMIDA.value).strip() or MealType.COMIDA.value
            if not recipe_name:
                continue
            items.append(
                MenuSuggestionItem(
                    day=day,
                    meal_type=MealType(meal_type),
                    recipe_name=recipe_name,
                    servings=max(int(servings_raw or "0"), 1),
                    notes=notes,
                )
            )
    with get_session() as session:
        MenuManager(session).save_week_menu(MenuSuggestion(week_start=week_start, items=items))
    return _redirect(f"/web/menu?week_start={week_start.isoformat()}&month={month_value}&notice=Menu%20guardado")


@router.post("/web/menu/suggest", dependencies=[Depends(require_auth)])
async def suggest_menu(request: Request) -> RedirectResponse:
    form = await request.form()
    week_start = date.fromisoformat(str(form.get("week_start")))
    month_value = str(form.get("month") or week_start.strftime("%Y-%m"))
    with get_session() as session:
        suggestion = AIAgent(session).suggest_week_menu(week_start)
        MenuManager(session).save_week_menu(suggestion)
    return _redirect(f"/web/menu?week_start={week_start.isoformat()}&month={month_value}&notice=Sugerencia%20IA%20generada%20y%20guardada")


@router.post("/web/menu/delete", dependencies=[Depends(require_auth)])
async def delete_menu(request: Request) -> RedirectResponse:
    form = await request.form()
    week_start = date.fromisoformat(str(form.get("week_start")))
    month_value = str(form.get("month") or week_start.strftime("%Y-%m"))
    with get_session() as session:
        deleted = MenuManager(session).delete_week_menu(week_start)
    notice = "Menu%20eliminado" if deleted else "No%20habia%20menu%20para%20esa%20semana"
    return _redirect(f"/web/menu?week_start={week_start.isoformat()}&month={month_value}&notice={notice}")


@router.get("/web/shopping", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def shopping_page(request: Request, notice: str | None = None) -> HTMLResponse:
    with get_session() as session:
        items = ShoppingList(session).generate()
        export_path = ShoppingList(session).export_text()
        context = _base_context(request, "Lista de compra", "shopping")
        context.update({"notice": notice, "items": items, "export_path": export_path})
    return templates.TemplateResponse("shopping.html", context)


@router.get("/web/recipes", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def recipes_page(request: Request, notice: str | None = None, edit: int | None = None) -> HTMLResponse:
    with get_session() as session:
        book = RecipeBook(session)
        recipes = book.list_recipes()
        recipe_to_edit = book.get_recipe(edit) if edit is not None else None
        form_recipe = {
            "id": recipe_to_edit.id if recipe_to_edit else None,
            "name": recipe_to_edit.name if recipe_to_edit else "",
            "description": recipe_to_edit.description if recipe_to_edit else "",
            "ingredients": _join_lines(recipe_to_edit.ingredients) if recipe_to_edit else "",
            "steps": _join_lines(recipe_to_edit.steps) if recipe_to_edit else "",
            "tags": _join_csv(recipe_to_edit.tags) if recipe_to_edit else "",
            "servings": recipe_to_edit.servings if recipe_to_edit else 4,
            "source_url": recipe_to_edit.source_url if recipe_to_edit else "",
        }
        context = _base_context(request, "Recetas", "recipes")
        context.update({"notice": notice, "recipes": recipes, "form_recipe": form_recipe, "editing_recipe": recipe_to_edit})
    return templates.TemplateResponse("recipes.html", context)


@router.post("/web/recipes", dependencies=[Depends(require_auth)])
async def create_recipe(request: Request) -> RedirectResponse:
    form = await request.form()
    payload = RecipeCreate(
        name=str(form.get("name") or "").strip(),
        description=str(form.get("description") or "").strip(),
        ingredients=_split_lines(str(form.get("ingredients") or "")),
        steps=_split_lines(str(form.get("steps") or "")),
        tags=_split_csv(str(form.get("tags") or "")),
        servings=max(int(str(form.get("servings") or "0")), 1),
        source_url=str(form.get("source_url") or "").strip(),
    )
    with get_session() as session:
        RecipeBook(session).add_recipe(payload)
    return _redirect("/web/recipes?notice=Receta%20creada")


@router.post("/web/recipes/{recipe_id}/update", dependencies=[Depends(require_auth)])
async def update_recipe(request: Request, recipe_id: int) -> RedirectResponse:
    form = await request.form()
    payload = RecipeCreate(
        name=str(form.get("name") or "").strip(),
        description=str(form.get("description") or "").strip(),
        ingredients=_split_lines(str(form.get("ingredients") or "")),
        steps=_split_lines(str(form.get("steps") or "")),
        tags=_split_csv(str(form.get("tags") or "")),
        servings=max(int(str(form.get("servings") or "0")), 1),
        source_url=str(form.get("source_url") or "").strip(),
    )
    with get_session() as session:
        updated = RecipeBook(session).update_recipe(recipe_id, payload)
    if updated is None:
        return _redirect("/web/recipes?notice=Receta%20no%20encontrada")
    return _redirect("/web/recipes?notice=Receta%20actualizada")


@router.post("/web/recipes/{recipe_id}/delete", dependencies=[Depends(require_auth)])
def delete_recipe(recipe_id: int) -> RedirectResponse:
    with get_session() as session:
        deleted = RecipeBook(session).delete_recipe(recipe_id)
    notice = "Receta%20eliminada" if deleted else "Receta%20no%20encontrada"
    return _redirect(f"/web/recipes?notice={notice}")


@router.get("/web/family", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def family_page(request: Request, notice: str | None = None, edit: int | None = None) -> HTMLResponse:
    with get_session() as session:
        family = FamilyProfile(session)
        members = family.list_members()
        member_to_edit = family.get_member(edit) if edit is not None else None
        form_member = {
            "id": member_to_edit.id if member_to_edit else None,
            "name": member_to_edit.name if member_to_edit else "",
            "age": member_to_edit.age if member_to_edit else "",
            "allergies": _join_csv(member_to_edit.allergies) if member_to_edit else "",
            "preferences": _join_csv(member_to_edit.preferences) if member_to_edit else "",
            "restrictions": _join_csv(member_to_edit.restrictions) if member_to_edit else "",
            "meals_per_day": member_to_edit.meals_per_day if member_to_edit else 2,
        }
        context = _base_context(request, "Familia", "family")
        context.update(
            {
                "notice": notice,
                "members": members,
                "family_context": family.family_context(),
                "form_member": form_member,
                "editing_member": member_to_edit,
            }
        )
    return templates.TemplateResponse("family.html", context)


@router.post("/web/family", dependencies=[Depends(require_auth)])
async def create_family_member(request: Request) -> RedirectResponse:
    form = await request.form()
    payload = FamilyMemberCreate(
        name=str(form.get("name") or "").strip(),
        age=max(int(str(form.get("age") or "0")), 0),
        allergies=_split_csv(str(form.get("allergies") or "")),
        preferences=_split_csv(str(form.get("preferences") or "")),
        restrictions=_split_csv(str(form.get("restrictions") or "")),
        meals_per_day=max(int(str(form.get("meals_per_day") or "0")), 1),
    )
    with get_session() as session:
        FamilyProfile(session).add_member(payload)
    return _redirect("/web/family?notice=Miembro%20anadido")


@router.post("/web/family/{member_id}/update", dependencies=[Depends(require_auth)])
async def update_family_member(request: Request, member_id: int) -> RedirectResponse:
    form = await request.form()
    payload = FamilyMemberCreate(
        name=str(form.get("name") or "").strip(),
        age=max(int(str(form.get("age") or "0")), 0),
        allergies=_split_csv(str(form.get("allergies") or "")),
        preferences=_split_csv(str(form.get("preferences") or "")),
        restrictions=_split_csv(str(form.get("restrictions") or "")),
        meals_per_day=max(int(str(form.get("meals_per_day") or "0")), 1),
    )
    with get_session() as session:
        updated = FamilyProfile(session).update_member(member_id, payload)
    if updated is None:
        return _redirect("/web/family?notice=Miembro%20no%20encontrado")
    return _redirect("/web/family?notice=Miembro%20actualizado")


@router.post("/web/family/{member_id}/delete", dependencies=[Depends(require_auth)])
def delete_family_member(member_id: int) -> RedirectResponse:
    with get_session() as session:
        deleted = FamilyProfile(session).delete_member(member_id)
    notice = "Miembro%20eliminado" if deleted else "Miembro%20no%20encontrado"
    return _redirect(f"/web/family?notice={notice}")


@router.get("/web/assistant", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def assistant_page(request: Request) -> HTMLResponse:
    context = _base_context(request, "Asistente", "assistant")
    context.update({"message": "", "answer": None})
    return templates.TemplateResponse("assistant.html", context)


@router.post("/web/assistant", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def assistant_chat(request: Request) -> HTMLResponse:
    form = await request.form()
    message = str(form.get("message") or "").strip()
    with get_session() as session:
        answer = FamilyAssistant(session).answer(message)
    context = _base_context(request, "Asistente", "assistant")
    context.update({"message": message, "answer": answer})
    return templates.TemplateResponse("assistant.html", context)


@router.get("/web/system", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
def system_page(request: Request, notice: str | None = None) -> HTMLResponse:
    config = load_file_config()
    server = MCPServerLocal()
    context = _base_context(request, "Sistema", "system")
    context.update(
        {
            "notice": notice,
            "api_host": config.api.host,
            "api_port": config.api.port,
            "mcp_name": server.name,
            "mcp_tools": sorted(server.tools().keys()),
            "mcp_resources": server.resources(),
        }
    )
    return templates.TemplateResponse("system.html", context)


@router.post("/web/system/init-db", dependencies=[Depends(require_auth)])
def web_init_db() -> RedirectResponse:
    init_db()
    return _redirect("/web/system?notice=Base%20de%20datos%20inicializada")


@router.post("/web/system/seed-demo", dependencies=[Depends(require_auth)])
def web_seed_demo() -> RedirectResponse:
    init_db()
    with get_session() as session:
        seed_demo_data(session)
    return _redirect("/web/system?notice=Datos%20demo%20cargados")
