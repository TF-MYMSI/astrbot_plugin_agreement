"""存储层封装"""

from typing import Optional
from astrbot.api.star import Star
from .models import AgreementState


class AgreementStorage:
    """协议数据存储"""

    def __init__(self, star: Star):
        self.star = star

    def _get_session_key(self, user_id: str, group_id: Optional[str] = None) -> str:
        if group_id:
            return f"doc_agree_{group_id}_{user_id}"
        return f"doc_agree_{user_id}"

    def _get_stat_key(self, group_id: Optional[str] = None) -> str:
        if group_id:
            return f"doc_stat_group_{group_id}"
        return "doc_stat_private"

    async def get_state(self, user_id: str, group_id: Optional[str] = None) -> Optional[AgreementState]:
        key = self._get_session_key(user_id, group_id)
        return await self.star.get_kv_data(key, None)

    async def set_state(self, user_id: str, state: Optional[AgreementState], group_id: Optional[str] = None) -> None:
        key = self._get_session_key(user_id, group_id)
        await self.star.put_kv_data(key, state)

    async def get_user_data(self, user_id: str, field: str, default=0, group_id: Optional[str] = None):
        key = f"{self._get_session_key(user_id, group_id)}_{field}"
        return await self.star.get_kv_data(key, default)

    async def set_user_data(self, user_id: str, field: str, value, group_id: Optional[str] = None) -> None:
        key = f"{self._get_session_key(user_id, group_id)}_{field}"
        await self.star.put_kv_data(key, value)

    async def add_to_user_list(self, user_id: str, group_id: Optional[str] = None) -> None:
        stat_key = self._get_stat_key(group_id)
        user_list = await self.star.get_kv_data(f"{stat_key}_users", [])
        if user_id not in user_list:
            user_list.append(user_id)
            await self.star.put_kv_data(f"{stat_key}_users", user_list)
            await self._update_stat(stat_key, "total")

    async def update_stat(self, field: str, delta: int = 1, group_id: Optional[str] = None) -> None:
        stat_key = self._get_stat_key(group_id)
        await self._update_stat(stat_key, field, delta)

    async def _update_stat(self, stat_key: str, field: str, delta: int = 1) -> None:
        key = f"{stat_key}_{field}"
        current = await self.star.get_kv_data(key, 0)
        await self.star.put_kv_data(key, current + delta)

    async def get_stat(self, group_id: Optional[str] = None) -> dict:
        stat_key = self._get_stat_key(group_id)
        return {
            "total": await self.star.get_kv_data(f"{stat_key}_total", 0),
            "agreed": await self.star.get_kv_data(f"{stat_key}_agreed", 0),
            "refused": await self.star.get_kv_data(f"{stat_key}_refused", 0),
            "users": await self.star.get_kv_data(f"{stat_key}_users", []),
        }

    async def reset_stat(self, group_id: Optional[str] = None) -> None:
        stat_key = self._get_stat_key(group_id)
        await self.star.put_kv_data(f"{stat_key}_total", 0)
        await self.star.put_kv_data(f"{stat_key}_agreed", 0)
        await self.star.put_kv_data(f"{stat_key}_refused", 0)
        await self.star.put_kv_data(f"{stat_key}_users", [])
