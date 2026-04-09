"""协议签订流程处理"""

import time
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger

from ..core import (
    PluginConfig, AgreementState, AgreementStorage,
    is_at_me, extract_group_id, extract_user_id,
    match_keyword
)


class MessageHandler:
    """协议签订消息处理器"""

    def __init__(self, config: PluginConfig, storage: AgreementStorage, bot_qq: str):
        self.config = config
        self.storage = storage
        self.bot_qq = bot_qq
        logger.info(f"MessageHandler 初始化完成, bot_qq={bot_qq}")

    def _remove_at_mention(self, msg: str) -> str:
        """移除消息中的@机器人部分"""
        if not self.bot_qq:
            return msg
        msg = msg.replace(f"@{self.bot_qq}", "")
        msg = msg.replace(f"[CQ:at,qq={self.bot_qq}]", "")
        while "  " in msg:
            msg = msg.replace("  ", " ")
        return msg.strip()

    async def handle(self, event: AstrMessageEvent):
        """处理协议签订流程"""
        original_msg = event.message_str.strip()
        group_id = extract_group_id(event)
        user_id = extract_user_id(event)
        is_group = group_id is not None
        
        logger.info(f"[HANDLE] 进入, 消息='{original_msg}', 群聊={is_group}, 用户={user_id}")
        
        # ========== 群聊处理 ==========
        if is_group:
            logger.info(f"[HANDLE] 群聊, scope_group={self.config.scope_group}")
            if not self.config.scope_group:
                logger.info(f"[HANDLE] 群聊未启用，返回")
                return
            
            logger.info(f"[HANDLE] 检查@, bot_qq={self.bot_qq}")
            at_result = is_at_me(event, self.bot_qq)
            logger.info(f"[HANDLE] is_at_me={at_result}")
            if not at_result:
                logger.info(f"[HANDLE] 未@机器人，返回")
                return
            
            msg = self._remove_at_mention(original_msg)
            logger.info(f"[HANDLE] 移除@后消息='{msg}'")
        
        # ========== 私聊处理 ==========
        else:
            logger.info(f"[HANDLE] 私聊, scope_private={self.config.scope_private}")
            if not self.config.scope_private:
                logger.info(f"[HANDLE] 私聊未启用，返回")
                return
            msg = original_msg
            logger.info(f"[HANDLE] 私聊消息='{msg}'")
        
        # 获取用户状态
        status = await self.storage.get_state(user_id, group_id)
        logger.info(f"[HANDLE] 用户状态={status}")
        
        # ========== 状态: None ==========
        if status is None:
            logger.info(f"[HANDLE] 未签订，发送协议")
            await self.storage.set_state(user_id, AgreementState.WAITING, group_id)
            await self.storage.set_user_data(user_id, "last", time.time(), group_id)
            await self.storage.add_to_user_list(user_id, group_id)
            yield event.plain_result(self.config.build_document())
            event.stop_event()
            logger.info(f"[HANDLE] 协议已发送")
            return
        
        # ========== 状态: WAITING ==========
        if status == AgreementState.WAITING:
            logger.info(f"[HANDLE] 等待确认中, 消息='{msg}'")
            
            if match_keyword(msg, self.config.refuse_keywords):
                logger.info(f"[HANDLE] 匹配拒绝")
                await self.storage.set_state(user_id, AgreementState.REFUSED, group_id)
                await self.storage.set_user_data(user_id, "time", time.time(), group_id)
                await self.storage.update_stat("refused", 1, group_id)
                reply = self.config.format_reply(self.config.reply_refuse)
                if reply:
                    yield event.plain_result(reply)
                event.stop_event()
                return
            
            if match_keyword(msg, self.config.agree_keywords):
                logger.info(f"[HANDLE] 匹配同意")
                await self.storage.set_state(user_id, AgreementState.AGREED, group_id)
                await self.storage.set_user_data(user_id, "time", time.time(), group_id)
                await self.storage.update_stat("agreed", 1, group_id)
                reply = self.config.format_reply(self.config.reply_agree)
                if reply:
                    yield event.plain_result(reply)
                event.stop_event()
                return
            
            logger.info(f"[HANDLE] 无匹配，检查冷却")
            last_sent = await self.storage.get_user_data(user_id, "last", 0, group_id)
            if time.time() - last_sent < self.config.cooldown_seconds:
                logger.info(f"[HANDLE] 冷却中")
                reply = self.config.format_reply(self.config.reply_waiting)
                if reply:
                    reply = reply.replace("{name}", self.config.doc_name)
                    yield event.plain_result(reply)
            else:
                logger.info(f"[HANDLE] 重新发送协议")
                await self.storage.set_user_data(user_id, "last", time.time(), group_id)
                yield event.plain_result(self.config.build_document())
            event.stop_event()
            return
        
        # ========== 状态: AGREED ==========
        if status == AgreementState.AGREED:
            logger.info(f"[HANDLE] 已同意，放行")
            return
        
        # ========== 状态: REFUSED ==========
        if status == AgreementState.REFUSED:
            logger.info(f"[HANDLE] 已拒绝，静默")
            event.stop_event()
            return
        
        logger.info(f"[HANDLE] 未知状态: {status}")
