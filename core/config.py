"""配置管理"""

import re
from typing import List, Dict, Any


class PluginConfig:
    """插件配置类"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        # 触发词
        self.trigger_word = config_dict.get('trigger_word', '/agreement')
        
        # 同意/拒绝关键词
        self.agree_keywords = config_dict.get('agree_keywords', ['同意', '是的', '确认', 'agree', 'yes'])
        self.refuse_keywords = config_dict.get('refuse_keywords', ['不同意', '拒绝', '否', 'refuse', 'no'])
        
        # 文档内容
        self.delivery_text = config_dict.get('delivery_text', '请阅读并同意以下协议：\n\n协议内容')
        
        # 回复文案
        self.reply_agree = config_dict.get('reply_agree', '✅ 您已同意协议，感谢您的配合！')
        self.reply_refuse = config_dict.get('reply_refuse', '')
        self.reply_waiting = config_dict.get('reply_waiting', '请回复「同意」或「不同意」。')
        
        # 作用范围
        self.scope_group = config_dict.get('scope_group', True)
        self.scope_private = config_dict.get('scope_private', True)
        
        # 冷却时间（秒）
        self.cooldown_seconds = config_dict.get('cooldown_seconds', 10)
        
        # 反悔限制
        self.undo_max_count = config_dict.get('undo_max_count', 3)
        self.undo_cooldown_hours = config_dict.get('undo_cooldown_hours', 24)
        
        # 管理员列表
        self.admin_users = config_dict.get('admin_users', [])
    
    def build_document(self) -> str:
        """构建完整文档内容"""
        return self.delivery_text
    
    def format_reply(self, reply: str) -> str:
        """格式化回复，支持变量替换"""
        if not reply:
            return ""
        # 可以在这里添加变量替换逻辑
        return reply


class AgreementState:
    """协议状态常量"""
    WAITING = "waiting"   # 等待确认
    AGREED = "agreed"     # 已同意
    REFUSED = "refused"   # 已拒绝
