from __future__ import annotations

from datetime import date

from sqlmodel import Session

from app.ai.agent import AIAgent
from app.core.family import FamilyProfile
from app.core.menu_manager import DAYS
from app.core.menu_manager import MenuManager


class FamilyAssistant:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.agent = AIAgent(session)
        self.family = FamilyProfile(session)
        self.menu_manager = MenuManager(session)

    def answer(self, message: str) -> str:
        normalized = message.lower()
        if "que como hoy" in normalized or "qué como hoy" in normalized:
            today_name = DAYS[date.today().weekday()]
            items = self.menu_manager.as_week_table().get(today_name, [])
            return items[0].recipe_name if items else "No hay menu cargado para hoy."
        if "sin gluten" in normalized:
            return "Puedo generar una semana sin gluten con suggest-week y guardarla en la BD."
        if "sustituye" in normalized:
            return "Indica la receta a sustituir y puedo regenerar el dia correspondiente."
        context = self.family.family_context()
        return f"Asistente familiar activo. Miembros actuales: {context['count']}."
