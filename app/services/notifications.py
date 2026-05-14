from __future__ import annotations

import httpx

from app.models.db import load_file_config


class NotificationService:
    def __init__(self) -> None:
        self.config = load_file_config().notifications

    def send(self, message: str) -> bool:
        if not self.config.enabled or not self.config.ntfy_topic:
            return False
        response = httpx.post(f"https://ntfy.sh/{self.config.ntfy_topic}", content=message, timeout=10.0)
        response.raise_for_status()
        return True
