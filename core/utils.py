"""工具函数"""

from typing import List, Optional
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger


def is_admin(uid: str, admins: List[str]) -> bool:
    return uid in admins


def contains_keyword(text: str, keywords: List[str]) -> bool:
    return any(kw in text for kw in keywords)


def match_keyword(text: str, keywords: List[str]) -> bool:
    """精确匹配关键词（解决「不同意」被「同意」误判）"""
    if not keywords:
        return False
    
    # 精确匹配
    if text in keywords:
        return True
    
    # 按标点分割后匹配
    import re
    for seg in re.split(r'[，,。！？；;:：\s]+', text):
        if seg in keywords:
            return True
    
    return False


def extract_user_id(event: AstrMessageEvent) -> str:
    return event.get_sender_id()


def extract_group_id(event: AstrMessageEvent) -> Optional[str]:
    try:
        group_id = event.get_group_id()
        return group_id if group_id and group_id != "" else None
    except:
        return None


def is_private_chat(event: AstrMessageEvent) -> bool:
    return extract_group_id(event) is None


def is_at_me(event: AstrMessageEvent, bot_qq: str) -> bool:
    """检查是否@了机器人（增强版）"""
    if not bot_qq:
        return False
    
    try:
        # 方法1：使用内置方法
        if hasattr(event, 'is_at_me'):
            result = event.is_at_me()
            if result:
                logger.debug(f"is_at_me: 内置方法返回 True")
                return True
    except Exception as e:
        logger.debug(f"is_at_me 内置方法异常: {e}")
    
    try:
        # 方法2：遍历消息段
        for segment in event.get_messages():
            if segment.type == "At":
                # 获取被@的QQ号
                qq = None
                if hasattr(segment, 'qq'):
                    qq = str(segment.qq)
                elif hasattr(segment, 'target'):
                    qq = str(segment.target)
                elif isinstance(segment.data, dict):
                    qq = segment.data.get('qq', '')
                
                if qq and str(qq) == str(bot_qq):
                    logger.debug(f"is_at_me: 消息段匹配到 {qq}")
                    return True
    except Exception as e:
        logger.debug(f"is_at_me 遍历消息段异常: {e}")
    
    try:
        # 方法3：检查消息文本
        msg = event.message_str
        if f"@{bot_qq}" in msg:
            logger.debug(f"is_at_me: 文本匹配 @{bot_qq}")
            return True
        if f"[CQ:at,qq={bot_qq}]" in msg:
            logger.debug(f"is_at_me: CQ码匹配 {bot_qq}")
            return True
    except Exception as e:
        logger.debug(f"is_at_me 文本匹配异常: {e}")
    
    logger.debug(f"is_at_me: 未匹配到 @{bot_qq}")
    return False


def remove_at_mention(msg: str, bot_qq: str) -> str:
    """移除消息中的@机器人部分"""
    if not bot_qq:
        return msg
    
    # 移除 @qq 格式
    msg = msg.replace(f"@{bot_qq}", "")
    # 移除 CQ码格式
    msg = msg.replace(f"[CQ:at,qq={bot_qq}]", "")
    # 移除可能的多余空格
    while "  " in msg:
        msg = msg.replace("  ", " ")
    return msg.strip()
