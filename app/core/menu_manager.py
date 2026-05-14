from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlmodel import Session, delete, select

from app.models.schemas import MenuEntry, MenuSuggestion


DAYS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


class MenuManager:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_current_week_start(self) -> date:
        today = date.today()
        return today - timedelta(days=today.weekday())

    def list_week_menu(self, week_start: date | None = None) -> list[MenuEntry]:
        week_start = week_start or self.get_current_week_start()
        statement = select(MenuEntry).where(MenuEntry.week_start == week_start).order_by(MenuEntry.day)
        return list(self.session.exec(statement).all())

    def save_week_menu(self, suggestion: MenuSuggestion) -> list[MenuEntry]:
        self.session.exec(delete(MenuEntry).where(MenuEntry.week_start == suggestion.week_start))
        entries: list[MenuEntry] = []
        for item in suggestion.items:
            entry = MenuEntry(
                week_start=suggestion.week_start,
                day=item.day,
                meal_type=item.meal_type,
                recipe_name=item.recipe_name,
                servings=item.servings,
                notes=item.notes,
            )
            self.session.add(entry)
            entries.append(entry)
        self.session.commit()
        for entry in entries:
            self.session.refresh(entry)
        return entries

    def delete_week_menu(self, week_start: date) -> int:
        entries = self.list_week_menu(week_start)
        if not entries:
            return 0
        self.session.exec(delete(MenuEntry).where(MenuEntry.week_start == week_start))
        self.session.commit()
        return len(entries)

    def list_saved_week_starts(self, start_date: date, end_date: date) -> list[date]:
        statement = (
            select(MenuEntry.week_start)
            .where(MenuEntry.week_start >= start_date, MenuEntry.week_start <= end_date)
            .distinct()
            .order_by(MenuEntry.week_start)
        )
        return list(self.session.exec(statement).all())

    def as_week_table(self, week_start: date | None = None) -> dict[str, list[MenuEntry]]:
        grouped: dict[str, list[MenuEntry]] = defaultdict(list)
        for entry in self.list_week_menu(week_start):
            grouped[entry.day].append(entry)
        return {day: grouped.get(day, []) for day in DAYS}

    @staticmethod
    def serialize_entry(entry: MenuEntry) -> dict:
        return {
            "id": entry.id,
            "week_start": entry.week_start.isoformat(),
            "day": entry.day,
            "meal_type": entry.meal_type,
            "recipe_name": entry.recipe_name,
            "servings": entry.servings,
            "notes": entry.notes,
            "created_at": entry.created_at.isoformat(),
        }
