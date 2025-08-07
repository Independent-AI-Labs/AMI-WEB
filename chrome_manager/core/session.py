import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
from loguru import logger

from .instance import BrowserInstance


class SessionData:
    def __init__(
        self,
        session_id: str,
        cookies: list[dict],
        local_storage: dict[str, str],
        session_storage: dict[str, str],
        url: str,
        window_size: tuple,
        user_agent: str | None = None,
    ):
        self.session_id = session_id
        self.cookies = cookies
        self.local_storage = local_storage
        self.session_storage = session_storage
        self.url = url
        self.window_size = window_size
        self.user_agent = user_agent
        self.created_at = datetime.now()


class SessionManager:
    def __init__(self, session_dir: str = "./sessions"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, SessionData] = {}

    async def initialize(self):
        logger.info(f"Initializing session manager with directory: {self.session_dir}")
        await self._load_existing_sessions()

    async def shutdown(self):
        logger.info("Shutting down session manager")
        self._sessions.clear()

    async def save_session(self, instance: BrowserInstance) -> str:
        if not instance.driver:
            raise ValueError("Instance has no active driver")

        session_id = f"session_{instance.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        cookies = instance.driver.get_cookies()

        local_storage = instance.driver.execute_script(
            """
            const items = {};
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                items[key] = localStorage.getItem(key);
            }
            return items;
        """
        )

        session_storage = instance.driver.execute_script(
            """
            const items = {};
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                items[key] = sessionStorage.getItem(key);
            }
            return items;
        """
        )

        window_size = instance.driver.get_window_size()

        session_data = SessionData(
            session_id=session_id,
            cookies=cookies,
            local_storage=local_storage,
            session_storage=session_storage,
            url=instance.driver.current_url,
            window_size=(window_size["width"], window_size["height"]),
            user_agent=instance._options.user_agent if instance._options else None,
        )

        await self._save_to_disk(session_data)
        self._sessions[session_id] = session_data

        logger.info(f"Saved session {session_id}")
        return session_id

    async def restore_session(self, session_id: str) -> BrowserInstance:
        session_data = self._sessions.get(session_id)
        if not session_data:
            session_data = await self._load_from_disk(session_id)
            if not session_data:
                raise ValueError(f"Session {session_id} not found")

        instance = BrowserInstance()
        await instance.launch(headless=True, options=None)

        instance.driver.get(session_data.url)

        for cookie in session_data.cookies:
            try:
                instance.driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"Failed to restore cookie: {e}")

        instance.driver.execute_script(
            """
            arguments[0].forEach(([key, value]) => {
                localStorage.setItem(key, value);
            });
        """,
            list(session_data.local_storage.items()),
        )

        instance.driver.execute_script(
            """
            arguments[0].forEach(([key, value]) => {
                sessionStorage.setItem(key, value);
            });
        """,
            list(session_data.session_storage.items()),
        )

        instance.driver.set_window_size(session_data.window_size[0], session_data.window_size[1])

        instance.driver.refresh()

        logger.info(f"Restored session {session_id}")
        return instance

    async def list_sessions(self) -> list[dict[str, Any]]:
        sessions = []
        for session_id, session_data in self._sessions.items():
            sessions.append(
                {
                    "session_id": session_id,
                    "url": session_data.url,
                    "created_at": session_data.created_at.isoformat(),
                    "cookie_count": len(session_data.cookies),
                }
            )

        for file_path in self.session_dir.glob("*.json"):
            session_id = file_path.stem
            if session_id not in self._sessions:
                try:
                    async with aiofiles.open(file_path) as f:
                        data = json.loads(await f.read())
                        sessions.append(
                            {
                                "session_id": session_id,
                                "url": data.get("url"),
                                "created_at": data.get("created_at"),
                                "cookie_count": len(data.get("cookies", [])),
                            }
                        )
                except Exception as e:
                    logger.error(f"Failed to read session file {file_path}: {e}")

        return sessions

    async def delete_session(self, session_id: str) -> bool:
        self._sessions.pop(session_id, None)

        file_path = self.session_dir / f"{session_id}.json"
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted session {session_id}")
            return True

        return False

    async def cleanup_expired_sessions(self, max_age_days: int = 7):
        cutoff = datetime.now().timestamp() - (max_age_days * 24 * 3600)
        deleted_count = 0

        for file_path in self.session_dir.glob("*.json"):
            if file_path.stat().st_mtime < cutoff:
                file_path.unlink()
                deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} expired sessions")

    async def _save_to_disk(self, session_data: SessionData):
        file_path = self.session_dir / f"{session_data.session_id}.json"

        data = {
            "session_id": session_data.session_id,
            "cookies": session_data.cookies,
            "local_storage": session_data.local_storage,
            "session_storage": session_data.session_storage,
            "url": session_data.url,
            "window_size": session_data.window_size,
            "user_agent": session_data.user_agent,
            "created_at": session_data.created_at.isoformat(),
        }

        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def _load_from_disk(self, session_id: str) -> SessionData | None:
        file_path = self.session_dir / f"{session_id}.json"

        if not file_path.exists():
            return None

        try:
            async with aiofiles.open(file_path) as f:
                data = json.loads(await f.read())

            session_data = SessionData(
                session_id=data["session_id"],
                cookies=data["cookies"],
                local_storage=data["local_storage"],
                session_storage=data["session_storage"],
                url=data["url"],
                window_size=tuple(data["window_size"]),
                user_agent=data.get("user_agent"),
            )
            session_data.created_at = datetime.fromisoformat(data["created_at"])

            return session_data

        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    async def _load_existing_sessions(self):
        for file_path in self.session_dir.glob("*.json"):
            session_id = file_path.stem
            session_data = await self._load_from_disk(session_id)
            if session_data:
                self._sessions[session_id] = session_data

        logger.info(f"Loaded {len(self._sessions)} existing sessions")
