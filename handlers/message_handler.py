"""统一消息处理（包括命令和协议签订流程）"""

import time
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from astrbot.api.message_components import Plain

from ..core import (
    PluginConfig, AgreementState, AgreementStorage,
    is_at_me, extract_group_id, extract_user_id,
    match_keyword
)


class MessageHandler:
    """统一消息处理器"""

    def __init__(self, config: PluginConfig, storage: AgreementStorage, bot_qq: str):
        self.config = config
        self.storage = storage
        self.bot_qq = bot_qq
        
        if not isinstance(self.config, PluginConfig):
            logger.error(f"MessageHandler: config 类型错误，应为 PluginConfig，实际为 {type(self.config)}")

    async def handle(self, event: AstrMessageEvent):
        """统一处理所有消息"""
        
        # 防御性检查
        if not isinstance(self.config, PluginConfig):
            logger.error(f"配置类型错误: {type(self.config)}")
            return
        
        msg = event.message_str.strip()
        if not msg:
            return
        
        # ========== 处理命令 ==========
        if msg == '/doc_status':
            async for r in self._cmd_status(event):
                yield r
            event.stop_event()
            return
        
        if msg == '/doc_undo':
            async for r in self._cmd_undo(event):
                yield r
            event.stop_event()
            return
        
        if msg == '/doc_help':
            async for r in self._cmd_help(event):
                yield r
            event.stop_event()
            return
        
        if msg == '/doc_stats':
            async for r in self._cmd_stats(event):
                yield r
            event.stop_event()
            return
        
        # ========== 处理协议签订 ==========
        async for r in self._handle_agreement(event):
            if r:
                yield r
    
    async def _cmd_status(self, event: AstrMessageEvent):
        """查看个人状态"""
        user_id = extract_user_id(event)
        group_id = extract_group_id(event)
        
        status = await self.storage.get_state(user_id, group_id)
        
        if status == AgreementState.AGREED:
            yield event.plain_result("✅ 您已经同意过协议。")
        elif status == AgreementState.REFUSED:
            yield event.plain_result("❌ 您之前拒绝了协议。")
        elif status == AgreementState.WAITING:
            yield event.plain_result("⏳ 您正在协议签订流程中，请回复「同意」或「不同意」。")
        else:
            yield event.plain_result("📋 您尚未签订协议。")
    
    async def _cmd_undo(self, event: AstrMessageEvent):
        """反悔重签"""
        user_id = extract_user_id(event)
        group_id = extract_group_id(event)
        
        await self.storage.set_state(user_id, None, group_id)
        await self.storage.set_user_data(user_id, "last", 0, group_id)
        
        yield event.plain_result("🔄 已清除您的协议状态，您可以重新签订。")
    
    async def _cmd_help(self, event: AstrMessageEvent):
        """帮助信息"""
        help_text = f"""📄 文档签订插件帮助

触发词：{self.config.trigger_word}
同意词：{', '.join(self.config.agree_keywords)}
拒绝词：{', '.join(self.config.refuse_keywords)}

命令：
/doc_status - 查看个人签订状态
/doc_undo - 反悔重新签订协议
/doc_help - 显示本帮助

回复「同意」或「不同意」完成签订。"""
        yield event.plain_result(help_text)
    
    async def _cmd_stats(self, event: AstrMessageEvent):
        """统计信息"""
        stats = await self.storage.get_stats()
        text = f"""📊 协议签订统计

✅ 已同意: {stats.get('agreed', 0)}
❌ 已拒绝: {stats.get('refused', 0)}
📋 等待中: {stats.get('waiting', 0)}"""
        yield event.plain_result(text)
    
    async def _handle_agreement(self, event: AstrMessageEvent):
        """处理协议签订流程"""
        
        if not self.config.delivery_text:
            return
        
        msg = event.message_str.strip()
        group_id = extract_group_id(event)
        user_id = extract_user_id(event)
        is_group = group_id is not None

        # 群聊检查@
        if is_group:
            if not self.config.scope_group:
                return
            if not is_at_me(event, self.bot_qq):
                return

        # 私聊检查
        if not is_group and not self.config.scope_private:
            return

        # 检查是否是触发词
        if msg != self.config.trigger_word:
            # 不是触发词，但可能在等待确认中，继续往下走
            pass

        # 获取用户状态
        status = await self.storage.get_state(user_id, group_id)

        try:
            # 未签订：检查是否是触发词
            if status is None:
                if msg == self.config.trigger_word:
                    logger.info(f"用户 {user_id} 未签订，发送协议")
                    await self.storage.set_state(user_id, AgreementState.WAITING, group_id)
                    await self.storage.set_user_data(user_id, "last", time.time(), group_id)
                    await self.storage.add_to_user_list(user_id, group_id)
                    yield event.plain_result(self.config.build_document())
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
                elif match_keyword(msg, self.config.agree_keywords):
                    logger.info(f"用户 {user_id} 同意文档")
                    await self.storage.set_state(user_id, AgreementState.AGREED, group_id)
                    await self.storage.set_user_data(user_id, "time", time.time(), group_id)
                    await self.storage.update_stat("agreed", 1, group_id)
                    yield event.plain_result(self.config.format_reply(self.config.reply_agree))
                else:
                    last_sent = await self.storage.get_user_data(user_id, "last", 0, group_id)
                    if time.time() - last_sent < self.config.cooldown_seconds:
                        reply = self.config.format_reply(self.config.reply_waiting)
                        if reply:
                            yield event.plain_result(reply)
                    else:
                        await self.storage.set_user_data(user_id, "last", time.time(), group_id)
                        yield event.plain_result(self.config.build_document())
                return

            # 已同意或已拒绝：放行或静默
            return

        except Exception as e:
            logger.error(f"文档插件处理消息时出错: {e}")
            import traceback
            traceback.print_exc()
            yield event.plain_result("处理消息时出现错误，请稍后再试。")
