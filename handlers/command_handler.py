"""命令处理"""

from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from astrbot.api.message_components import Plain

from ..core import PluginConfig, AgreementStorage, AgreementState


class CommandHandler:
    """命令处理器"""
    
    def __init__(self, config: PluginConfig, storage: AgreementStorage, context):
        self.config = config
        self.storage = storage
        self.context = context
    
    async def cmd_status(self, event: AstrMessageEvent):
        """查看个人状态"""
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else None
        
        status = await self.storage.get_state(user_id, group_id)
        
        if status == AgreementState.AGREED:
            yield event.plain_result("✅ 您已经同意过协议。")
        elif status == AgreementState.REFUSED:
            yield event.plain_result("❌ 您之前拒绝了协议。")
        elif status == AgreementState.WAITING:
            yield event.plain_result("⏳ 您正在协议签订流程中，请回复「同意」或「不同意」。")
        else:
            yield event.plain_result("📋 您尚未签订协议。")
    
    async def cmd_undo(self, event: AstrMessageEvent):
        """反悔重签"""
        user_id = str(event.get_sender_id())
        group_id = str(event.get_group_id()) if hasattr(event, 'get_group_id') else None
        
        # 清除状态
        await self.storage.set_state(user_id, None, group_id)
        await self.storage.set_user_data(user_id, "last", 0, group_id)
        
        yield event.plain_result("🔄 已清除您的协议状态，您可以重新签订。")
    
    async def cmd_help(self, event: AstrMessageEvent):
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
    
    async def cmd_stats(self, event: AstrMessageEvent):
        """统计信息"""
        stats = await self.storage.get_stats()
        text = f"""📊 协议签订统计

✅ 已同意: {stats.get('agreed', 0)}
❌ 已拒绝: {stats.get('refused', 0)}
📋 等待中: {stats.get('waiting', 0)}"""
        yield event.plain_result(text)
