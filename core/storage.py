# core/storage.py

import time
from astrbot.api import logger


class AgreementStorage:
    """协议状态存储（内存版本）"""
    
    def __init__(self, context):
        self.context = context
        # 使用内存字典存储
        self._data = {}
        self._stats = {}
        self._user_lists = {}
    
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
        return self._data.get(key)
    
    async def set_state(self, user_id: str, state, group_id: str = None):
        """设置用户状态"""
        key = self._get_key(user_id, group_id, "state")
        self._data[key] = state
    
    async def get_user_data(self, user_id: str, field: str, default=0, group_id: str = None):
        """获取用户数据"""
        key = self._get_key(user_id, group_id, field)
        return self._data.get(key, default)
    
    async def set_user_data(self, user_id: str, field: str, value, group_id: str = None):
        """设置用户数据"""
        key = self._get_key(user_id, group_id, field)
        self._data[key] = value
    
    async def add_to_user_list(self, user_id: str, group_id: str = None):
        """添加到用户列表"""
        list_key = f"userlist_{group_id}" if group_id else "userlist_private"
        if list_key not in self._user_lists:
            self._user_lists[list_key] = []
        if user_id not in self._user_lists[list_key]:
            self._user_lists[list_key].append(user_id)
    
    async def update_stat(self, stat_type: str, increment: int = 1, group_id: str = None):
        """更新统计"""
        stat_key = f"stats_{group_id}" if group_id else "stats_private"
        if stat_key not in self._stats:
            self._stats[stat_key] = {"agreed": 0, "refused": 0, "total": 0}
        self._stats[stat_key][stat_type] = self._stats[stat_key].get(stat_type, 0) + increment
        if stat_type in ["agreed", "refused"]:
            self._stats[stat_key]["total"] = self._stats[stat_key].get("total", 0) + 1
    
    async def get_stat(self, group_id: str = None):
        """获取统计"""
        stat_key = f"stats_{group_id}" if group_id else "stats_private"
        return self._stats.get(stat_key, {"agreed": 0, "refused": 0, "total": 0})
    
    async def get_user_list(self, group_id: str = None):
        """获取用户列表"""
        list_key = f"userlist_{group_id}" if group_id else "userlist_private"
        return self._user_lists.get(list_key, [])
    
    async def reset_stat(self, group_id: str = None):
        """重置统计"""
        stat_key = f"stats_{group_id}" if group_id else "stats_private"
        self._stats[stat_key] = {"agreed": 0, "refused": 0, "total": 0}
