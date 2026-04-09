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
        
        # ===== 调试日志1：进入函数 =====
        logger.info(f"[DEBUG1] 进入 handle, 原始消息='{original_msg}', 群聊={is_group}, 用户={user_id}, 群ID={group_id}")
        
        # ========== 群聊处理 ==========
        if is_group:
            logger.info(f"[DEBUG2] 群聊分支, scope_group={self.config.scope_group}")
            if not self.config.scope_group:
                logger.info(f"[DEBUG3] 群聊未启用，直接返回")
                return
            
            logger.info(f"[DEBUG4] 检查@, bot_qq={self.bot_qq}")
            at_result = is_at_me(event, self.bot_qq)
            logger.info(f"[DEBUG5] is_at_me 返回结果: {at_result}")
            if not at_result:
                logger.info(f"[DEBUG6] 未@机器人，直接返回")
                return
            
            msg = self._remove_at_mention(original_msg)
            logger.info(f"[DEBUG7] 移除@后消息: '{msg}'")
        
        # ========== 私聊处理 ==========
        else:
            logger.info(f"[DEBUG8] 私聊分支, scope_private={self.config.scope_private}")
            if not self.config.scope_private:
                logger.info(f"[DEBUG9] 私聊未启用，直接返回")
                return
            msg = original_msg
            logger.info(f"[DEBUG10] 私聊消息: '{msg}'")
        
        # ========== 获取用户状态 ==========
        logger.info(f"[DEBUG11] 准备获取用户状态, user_id={user_id}, group_id={group_id}")
        status = await self.storage.get_state(user_id, group_id)
        logger.info(f"[DEBUG12] 用户状态: {status}")
        
        # ========== 状态: None (未签订) ==========
        if status is None:
            logger.info(f"[DEBUG13] 用户未签订，准备发送协议")
            await self.storage.set_state(user_id, AgreementState.WAITING, group_id)
            await self.storage.set_user_data(user_id, "last", time.time(), group_id)
            await self.storage.add_to_user_list(user_id, group_id)
            logger.info(f"[DEBUG14] 状态已更新为 WAITING，准备发送协议内容")
            yield event.plain_result(self.config.build_document())
            event.stop_event()
            logger.info(f"[DEBUG15] 协议已发送")
            return
        
        # ========== 状态: WAITING (等待确认) ==========
        if status == AgreementState.WAITING:
            logger.info(f"[DEBUG16] 用户等待确认中，消息='{msg}'")
            
            # 检查拒绝
            if match_keyword(msg, self.config.refuse_keywords):
                logger.info(f"[DEBUG17] 匹配到拒绝关键词")
                await self.storage.set_state(user_id, AgreementState.REFUSED, group_id)
                await self.storage.set_user_data(user_id, "time", time.time(), group_id)
                await self.storage.update_stat("refused", 1, group_id)
                reply = self.config.format_reply(self.config.reply_refuse)
                if reply:
                    yield event.plain_result(reply)
                event.stop_event()
                return
            
            # 检查同意
            if match_keyword(msg, self.config.agree_keywords):
                logger.info(f"[DEBUG18] 匹配到同意关键词")
                await self.storage.set_state(user_id, AgreementState.AGREED, group_id)
                await self.storage.set_user_data(user_id, "time", time.time(), group_id)
                await self.storage.update_stat("agreed", 1, group_id)
                reply = self.config.format_reply(self.config.reply_agree)
                if reply:
                    yield event.plain_result(reply)
                event.stop_event()
                return
            
            # 其他回复：检查冷却
            logger.info(f"[DEBUG19] 未匹配到同意或拒绝，检查冷却")
            last_sent = await self.storage.get_user_data(user_id, "last", 0, group_id)
            logger.info(f"[DEBUG20] 上次发送时间: {last_sent}, 当前时间: {time.time()}, 冷却时间: {self.config.cooldown_seconds}")
            if time.time() - last_sent < self.config.cooldown_seconds:
                logger.info(f"[DEBUG21] 冷却期内，发送等待提示")
                reply = self.config.format_reply(self.config.reply_waiting)
                if reply:
                    reply = reply.replace("{name}", self.config.doc_name)
                    yield event.plain_result(reply)
            else:
                logger.info(f"[DEBUG22] 冷却期过，重新发送协议")
                await self.storage.set_user_data(user_id, "last", time.time(), group_id)
                yield event.plain_result(self.config.build_document())
            event.stop_event()
            return
        
        # ========== 状态: AGREED (已同意) ==========
        if status == AgreementState.AGREED:
            logger.info(f"[DEBUG23] 用户已同意，放行消息（不回复）")
            return
        
        # ========== 状态: REFUSED (已拒绝) ==========
        if status == AgreementState.REFUSED:
            logger.info(f"[DEBUG24] 用户已拒绝，静默")
            event.stop_event()
            return
        
        logger.info(f"[DEBUG25] 未知状态: {status}")
