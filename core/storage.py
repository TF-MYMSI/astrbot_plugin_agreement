# core/storage.py

import json
from astrbot.api.star import Context
from astrbot.api import logger


class AgreementStorage:
    """协议状态存储"""
    
    def __init__(self, context: Context):
        self.context = context
    
    def _get_key(self, user_id: str, group_id: str = None, suffix: str = ""):
        """生成存储 key"""
        if group_id:
            key = f"agreement_{group_id}_{user_id}"
        else:
            key = f"agreement_private_{user_id}"
        if suffix:
            key = f"{key}_{suffix}"
        return key
    
    async def get_state(self, user_id: str, group_id: str = None):
        """获取用户状态"""
        key = self._get_key(user_id, group_id, "state")
        try:
            return await self.context.db.get(key)
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            return None
    
    async def set_state(self, user_id: str, state, group_id: str = None):
        """设置用户状态"""
        key = self._get_key(user_id, group_id, "state")
        try:
            await self.context.db.set(key, state)
        except Exception as e:
            logger.error(f"设置状态失败: {e}")
    
    async def get_user_data(self, user_id: str, field: str, default=0, group_id: str = None):
        """获取用户数据"""
        key = self._get_key(user_id, group_id, field)
        try:
            value = await self.context.db.get(key)
            return value if value is not None else default
        except Exception as e:
            logger.error(f"获取用户数据失败: {e}")
            return default
    
    async def set_user_data(self, user_id: str, field: str, value, group_id: str = None):
        """设置用户数据"""
        key = self._get_key(user_id, group_id, field)
        try:
            await self.context.db.set(key, value)
        except Exception as e:
            logger.error(f"设置用户数据失败: {e}")
    
    async def add_to_user_list(self, user_id: str, group_id: str = None):
        """添加到用户列表"""
        list_key = f"agreement_userlist_{group_id}" if group_id else "agreement_userlist_private"
        try:
            users = await self.context.db.get(list_key) or []
            if user_id not in users:
                users.append(user_id)
                await self.context.db.set(list_key, users)
        except Exception as e:
            logger.error(f"添加到用户列表失败: {e}")
    
    async def update_stat(self, stat_type: str, increment: int = 1, group_id: str = None):
        """更新统计"""
        stat_key = f"agreement_stats_{group_id}" if group_id else "agreement_stats_private"
        try:
            stats = await self.context.db.get(stat_key) or {"agreed": 0, "refused": 0, "total": 0}
            stats[stat_type] = stats.get(stat_type, 0) + increment
            if stat_type == "agreed" or stat_type == "refused":
                stats["total"] = stats.get("total", 0) + 1
            await self.context.db.set(stat_key, stats)
        except Exception as e:
            logger.error(f"更新统计失败: {e}")
    
    async def get_stat(self, group_id: str = None):
        """获取统计"""
        stat_key = f"agreement_stats_{group_id}" if group_id else "agreement_stats_private"
        try:
            stats = await self.context.db.get(stat_key) or {"agreed": 0, "refused": 0, "total": 0}
            return stats
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {"agreed": 0, "refused": 0, "total": 0}
    
    async def get_user_list(self, group_id: str = None):
        """获取用户列表"""
        list_key = f"agreement_userlist_{group_id}" if group_id else "agreement_userlist_private"
        try:
            users = await self.context.db.get(list_key) or []
            return users
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return []
    
    async def reset_stat(self, group_id: str = None):
        """重置统计"""
        stat_key = f"agreement_stats_{group_id}" if group_id else "agreement_stats_private"
        try:
            await self.context.db.set(stat_key, {"agreed": 0, "refused": 0, "total": 0})
        except Exception as e:
            logger.error(f"重置统计失败: {e}")
