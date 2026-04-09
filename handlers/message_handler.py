"""协议签订流程处理"""

import time
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger

from ..core import (
    PluginConfig, AgreementState, AgreementStorage,
    is_at_me, extract_group_id, extract_user_id,
    match_keyword, is_admin
)


class MessageHandler:
    """协议签订消息处理器（不处理命令）"""

    def __init__(self, config: PluginConfig, storage: AgreementStorage, bot_qq: str):
        self.config = config
        self.storage = storage
        self.bot_qq = bot_qq

    async def handle(self, event: AstrMessageEvent):
        """处理协议签订流程"""
        msg = event.message_str.strip()
        group_id = extract_group_id(event)
        user_id = extract_user_id(event)
        is_group = group_id is not None
        
        # 群聊检查@（只有群聊需要@机器人）
        if is_group:
            if not self.config.scope_group:
                return
            if not is_at_me(event, self.bot_qq):
                return
        
        # 私聊检查
        if not is_group and not self.config.scope_private:
            return
        
        # 获取用户状态
        status = await self.storage.get_state(user_id, group_id)
        
        # ========== 状态: None (未签订) ==========
        # 用户发送任何消息都触发协议发送
        if status is None:
            logger.info(f"用户 {user_id} 未签订，发送协议")
            await self.storage.set_state(user_id, AgreementState.WAITING, group_id)
            await self.storage.set_user_data(user_id, "last", time.time(), group_id)
            await self.storage.add_to_user_list(user_id, group_id)
            yield event.plain_result(self.config.build_document())
            event.stop_event()
            return
        
        # ========== 状态: WAITING (等待确认) ==========
        if status == AgreementState.WAITING:
            # 先检查拒绝（让拒绝优先处理）
            if match_keyword(msg, self.config.refuse_keywords):
                logger.info(f"用户 {user_id} 拒绝文档")
                await self.storage.set_state(user_id, AgreementState.REFUSED, group_id)
                await self.storage.set_user_data(user_id, "time", time.time(), group_id)
                await self.storage.update_stat("refused", 1, group_id)
                reply = self.config.format_reply(self.config.reply_refuse)
                if reply:
                    yield event.plain_result(reply)
                event.stop_event()
                return
            
            # 再检查同意
            if match_keyword(msg, self.config.agree_keywords):
                logger.info(f"用户 {user_id} 同意文档")
                await self.storage.set_state(user_id, AgreementState.AGREED, group_id)
                await self.storage.set_user_data(user_id, "time", time.time(), group_id)
                await self.storage.update_stat("agreed", 1, group_id)
                reply = self.config.format_reply(self.config.reply_agree)
                if reply:
                    yield event.plain_result(reply)
                event.stop_event()
                return
            
            # 不是同意也不是拒绝：检查冷却，重复发送协议
            last_sent = await self.storage.get_user_data(user_id, "last", 0, group_id)
            if time.time() - last_sent < self.config.cooldown_seconds:
                # 冷却期内，只提示等待
                reply = self.config.format_reply(self.config.reply_waiting)
                if reply:
                    yield event.plain_result(reply)
            else:
                # 冷却期过，重新发送协议
                await self.storage.set_user_data(user_id, "last", time.time(), group_id)
                yield event.plain_result(self.config.build_document())
            event.stop_event()
            return
        
        # ========== 状态: AGREED (已同意) ==========
        if status == AgreementState.AGREED:
            # 正常放行，不回复，让消息继续传递给其他插件
            return
        
        # ========== 状态: REFUSED (已拒绝) ==========
        if status == AgreementState.REFUSED:
            # 完全静默，不回复任何消息
            # 命令已经被 CommandHandler 处理了，这里只处理普通消息
            event.stop_event()
            return
