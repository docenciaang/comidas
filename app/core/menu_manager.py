from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlmodel import Session, delete, select

from app.models.schemas import MenuEntry, MenuSuggestion


DAYS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
DAY_TO_OFFSET = {day: index for index, day in enumerate(DAYS)}


class MenuManager:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def normalize_week_start(target_date: date) -> date:
        return target_date - timedelta(days=target_date.weekday())

    def get_current_week_start(self) -> date:
        return self.normalize_week_start(date.today())

    def list_week_menu(self, week_start: date | None = None) -> list[MenuEntry]:
        week_start = self.normalize_week_start(week_start) if week_start else self.get_current_week_start()
        statement = select(MenuEntry).where(MenuEntry.week_start == week_start).order_by(MenuEntry.day)
        return list(self.session.exec(statement).all())

    def save_week_menu(self, suggestion: MenuSuggestion) -> list[MenuEntry]:
        normalized_week_start = self.normalize_week_start(suggestion.week_start)
        self.session.exec(delete(MenuEntry).where(MenuEntry.week_start == normalized_week_start))
        entries: list[MenuEntry] = []
        for item in suggestion.items:
            entry = MenuEntry(
                week_start=normalized_week_start,
                day=item.day,
                meal_type=(item.meal_type.value if hasattr(item.meal_type, "value") else str(item.meal_type)),
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
        week_start = self.normalize_week_start(week_start)
        entries = self.list_week_menu(week_start)
        if not entries:
            return 0
        self.session.exec(delete(MenuEntry).where(MenuEntry.week_start == week_start))
        self.session.commit()
        return len(entries)

    def list_saved_week_starts(self, start_date: date, end_date: date) -> list[date]:
        start_date = self.normalize_week_start(start_date)
        end_date = self.normalize_week_start(end_date)
        statement = (
            select(MenuEntry.week_start)
            .where(MenuEntry.week_start >= start_date, MenuEntry.week_start <= end_date)
            .distinct()
            .order_by(MenuEntry.week_start)
        )
        return list(self.session.exec(statement).all())

    def normalize_stored_week_starts(self) -> int:
        updated = 0
        for entry in self.session.exec(select(MenuEntry)).all():
            normalized = self.normalize_week_start(entry.week_start)
            if normalized != entry.week_start:
                entry.week_start = normalized
                self.session.add(entry)
                updated += 1
        if updated:
            self.session.commit()
        return updated

    def list_scheduled_dates(self, start_date: date, end_date: date) -> list[date]:
        start_date = self.normalize_week_start(start_date)
        end_date = end_date + timedelta(days=6 - end_date.weekday())
        statement = (
            select(MenuEntry.week_start, MenuEntry.day)
            .where(MenuEntry.week_start >= start_date, MenuEntry.week_start <= end_date)
            .distinct()
        )
        scheduled_dates: set[date] = set()
        for week_start, day_name in self.session.exec(statement).all():
            day_offset = DAY_TO_OFFSET.get(day_name)
            if day_offset is None:
                continue
            scheduled_day = week_start + timedelta(days=day_offset)
            if start_date <= scheduled_day <= end_date:
                scheduled_dates.add(scheduled_day)
        return sorted(scheduled_dates)

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
