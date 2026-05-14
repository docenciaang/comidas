from __future__ import annotations

from datetime import date

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from app.ai.agent import AIAgent
from app.ai.assistant import FamilyAssistant
from app.core.menu_manager import MenuManager
from app.core.shopping import ShoppingList
from app.models.db import get_session, init_db, load_file_config
from app.services.bootstrap import seed_demo_data


cli = typer.Typer(help="CLI del gestor de menus familiares")
console = Console()


@cli.command("init-db")
def init_db_command() -> None:
    init_db()
    console.print("[green]Base de datos inicializada[/green]")


@cli.command("seed-demo")
def seed_demo() -> None:
    init_db()
    with get_session() as session:
        seed_demo_data(session)
    console.print("[green]Datos demo cargados[/green]")


@cli.command("week")
def week() -> None:
    with get_session() as session:
        table = Table(title="Menu semanal")
        table.add_column("Dia")
        table.add_column("Tipo")
        table.add_column("Plato")
        table.add_column("Raciones")
        for day, entries in MenuManager(session).as_week_table().items():
            if not entries:
                table.add_row(day, "-", "-", "-")
                continue
            for entry in entries:
                table.add_row(day, entry.meal_type, entry.recipe_name, str(entry.servings))
        console.print(table)


@cli.command("suggest-week")
def suggest_week(week_start: str | None = None, save: bool = True) -> None:
    start = date.fromisoformat(week_start) if week_start else date.today()
    with get_session() as session:
        suggestion = AIAgent(session).suggest_week_menu(start)
        if save:
            MenuManager(session).save_week_menu(suggestion)
        console.print_json(data=suggestion.model_dump())


@cli.command("shopping-list")
def shopping_list() -> None:
    with get_session() as session:
        items = ShoppingList(session).generate()
    if not items:
        console.print("[yellow]No hay lista de compra disponible[/yellow]")
        return
    for item in items:
        console.print(f"- {item}")


@cli.command("serve-api")
def serve_api(reload: bool = True) -> None:
    config = load_file_config().api
    uvicorn.run("app.api:app", host=config.host, port=config.port, reload=reload)


@cli.command("ask")
def ask(message: str) -> None:
    with get_session() as session:
        answer = FamilyAssistant(session).answer(message)
    console.print(answer)


if __name__ == "__main__":
    cli()
