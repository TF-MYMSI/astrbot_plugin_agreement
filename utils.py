"""工具函数"""

from typing import List, Optional
from astrbot.api.event import AstrMessageEvent


def is_admin(uid: str, admins: List[str]) -> bool:
    return uid in admins


def contains_keyword(text: str, keywords: List[str]) -> bool:
    return any(kw in text for kw in keywords)


def match_keyword(text: str, keywords: List[str]) -> bool:
    text_lower = text.lower()
    for kw in keywords:
        if kw in text:
            return True
        if kw.lower() in text_lower:
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
