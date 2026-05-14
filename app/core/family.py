from __future__ import annotations

from pathlib import Path

import json
from sqlmodel import Session, select

from app.models.db import ROOT_DIR
from app.models.schemas import FamilyMember, FamilyMemberCreate, FamilyMemberUpdate


class FamilyProfile:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_members(self) -> list[FamilyMember]:
        return list(self.session.exec(select(FamilyMember).order_by(FamilyMember.name)).all())

    def get_member(self, member_id: int) -> FamilyMember | None:
        return self.session.get(FamilyMember, member_id)

    def add_member(self, member: FamilyMemberCreate) -> FamilyMember:
        record = FamilyMember(
            name=member.name,
            age=member.age,
            allergies=", ".join(member.allergies),
            preferences=", ".join(member.preferences),
            restrictions=", ".join(member.restrictions),
            meals_per_day=member.meals_per_day,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def update_member(self, member_id: int, member: FamilyMemberUpdate) -> FamilyMember | None:
        record = self.get_member(member_id)
        if record is None:
            return None
        record.name = member.name
        record.age = member.age
        record.allergies = ", ".join(member.allergies)
        record.preferences = ", ".join(member.preferences)
        record.restrictions = ", ".join(member.restrictions)
        record.meals_per_day = member.meals_per_day
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def delete_member(self, member_id: int) -> bool:
        record = self.get_member(member_id)
        if record is None:
            return False
        self.session.delete(record)
        self.session.commit()
        return True

    @staticmethod
    def serialize(member: FamilyMember) -> dict:
        return {
            "id": member.id,
            "name": member.name,
            "age": member.age,
            "allergies": [item.strip() for item in member.allergies.split(",") if item.strip()],
            "preferences": [item.strip() for item in member.preferences.split(",") if item.strip()],
            "restrictions": [item.strip() for item in member.restrictions.split(",") if item.strip()],
            "meals_per_day": member.meals_per_day,
        }

    def family_context(self) -> dict:
        members = self.list_members()
        allergies = sorted({item.strip() for m in members for item in m.allergies.split(",") if item.strip()})
        restrictions = sorted({item.strip() for m in members for item in m.restrictions.split(",") if item.strip()})
        return {
            "members": [m.name for m in members],
            "count": len(members),
            "allergies": allergies,
            "restrictions": restrictions,
        }

    def export_json(self) -> Path:
        output = ROOT_DIR / "data" / "family.json"
        payload = [
            {
                "name": member.name,
                "age": member.age,
                "allergies": [x.strip() for x in member.allergies.split(",") if x.strip()],
                "preferences": [x.strip() for x in member.preferences.split(",") if x.strip()],
                "restrictions": [x.strip() for x in member.restrictions.split(",") if x.strip()],
                "meals_per_day": member.meals_per_day,
            }
            for member in self.list_members()
        ]
        output.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return output
