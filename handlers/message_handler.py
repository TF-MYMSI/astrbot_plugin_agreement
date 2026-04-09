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
        
        # 检查是否是触发词
        is_trigger = any(match_keyword(msg, [kw]) for kw in self.config.trigger_keywords)
        
        # 如果不是触发词，检查是否在等待确认中
        status = await self.storage.get_state(user_id, group_id)
        
        # 既不是触发词，也不是等待确认状态，直接放行
        if not is_trigger and status != AgreementState.WAITING:
            return
        
        # 群聊检查@
        if is_group:
            if not self.config.scope_group:
                return
            if not is_at_me(event, self.bot_qq):
                return

        # 私聊检查
        if not is_group and not self.config.scope_private:
            return

        if not self.config.delivery_text:
            return

        try:
            # 未签订：发送协议
            if status is None:
                if is_trigger:
                    logger.info(f"用户 {user_id} 未签订，发送协议")
                    await self.storage.set_state(user_id, AgreementState.WAITING, group_id)
                    await self.storage.set_user_data(user_id, "last", time.time(), group_id)
                    await self.storage.add_to_user_list(user_id, group_id)
                    yield event.plain_result(self.config.build_document())
                    event.stop_event()
                return

            # 等待确认：处理同意/不同意
            if status == AgreementState.WAITING:
                if match_keyword(msg, self.config.refuse_keywords):
                    logger.info(f"用户 {user_id} 拒绝文档")
                    await self.storage.set_state(user_id, AgreementState.REFUSED, group_id)
                    await self.storage.set_user_data(user_id, "time", time.time(), group_id)
                    await self.storage.update_stat("refused", 1, group_id)
                    reply = self.config.format_reply(self.config.reply_refuse)
                    if reply:
                        yield event.plain_result(reply)
                    event.stop_event()
                elif match_keyword(msg, self.config.agree_keywords):
                    logger.info(f"用户 {user_id} 同意文档")
                    await self.storage.set_state(user_id, AgreementState.AGREED, group_id)
                    await self.storage.set_user_data(user_id, "time", time.time(), group_id)
                    await self.storage.update_stat("agreed", 1, group_id)
                    yield event.plain_result(self.config.format_reply(self.config.reply_agree))
                    event.stop_event()
                else:
                    last_sent = await self.storage.get_user_data(user_id, "last", 0, group_id)
                    if time.time() - last_sent < self.config.cooldown_seconds:
                        reply = self.config.format_reply(self.config.reply_waiting)
                        if reply:
                            yield event.plain_result(reply)
                    else:
                        await self.storage.set_user_data(user_id, "last", time.time(), group_id)
                        yield event.plain_result(self.config.build_document())
                    event.stop_event()
                return

            # 已同意或已拒绝：静默（不回复）
            return

        except Exception as e:
            logger.error(f"文档插件处理消息时出错: {e}")
            yield event.plain_result("处理消息时出现错误，请稍后再试。")
            event.stop_event()
