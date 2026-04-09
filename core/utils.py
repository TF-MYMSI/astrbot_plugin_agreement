"""工具函数"""

from typing import List, Optional
from astrbot.api.event import AstrMessageEvent


def is_admin(uid: str, admins: List[str]) -> bool:
    return uid in admins


def contains_keyword(text: str, keywords: List[str]) -> bool:
    return any(kw in text for kw in keywords)


def match_keyword(text: str, keywords: List[str]) -> bool:
    """精确匹配关键词（解决「不同意」被「同意」误判的问题）"""
    if not keywords:
        return False
    
    # 精确匹配：整个消息完全等于关键词
    if text in keywords:
        return True
    
    # 可选：按标点分割后匹配（支持「同意。好的」这种情况）
    import re
    for seg in re.split(r'[，,。！？；;:：\s]+', text):
        if seg in keywords:
            return True
    
    return False


def extract_user_id(event: AstrMessageEvent) -> str:
    return event.get_sender_id()


def extract_group_id(event: AstrMessageEvent) -> Optional[str]:
    group_id = event.get_group_id()
    return group_id if group_id and group_id != "" else None


def is_private_chat(event: AstrMessageEvent) -> bool:
    return extract_group_id(event) is None


def is_at_me(event: AstrMessageEvent, bot_qq: str) -> bool:
    try:
        return event.is_at_me()
    except AttributeError:
        msg = event.message_str
        for segment in event.get_messages():
            if segment.type == "At":
                qq = getattr(segment, 'qq', None) or getattr(segment, 'target', None) or str(segment)
                if str(qq) == bot_qq:
                    return True
        return f"@{bot_qq}" in msg
