"""文档签订插件主入口"""

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig

from core import PluginConfig, AgreementStorage, AgreementState, is_admin, extract_user_id, extract_group_id
from handlers import MessageHandler, CommandHandler


@register(
    "astrbot_plugin_agreement",
    "YourName",
    "文档签订插件",
    "1.0.0"
)
class AgreementPlugin(Star):
    """文档签订插件主类"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = PluginConfig(config)
        self.storage = AgreementStorage(self)
        self.bot_qq = str(context.get_bot_id()) if hasattr(context, 'get_bot_id') else ""
        self.message_handler = MessageHandler(self.config, self.storage, self.bot_qq)
        self.command_handler = CommandHandler(self.config, self.storage)
        self._log_config()

    def _log_config(self) -> None:
        logger.info(f"文档插件已加载 | 私聊: {self.config.scope_private} | 群聊: {self.config.scope_group}")
        logger.info(f"文档名称: {self.config.doc_name} | 反悔功能: {'启用' if self.config.allow_undo else '禁用'}")
        logger.info(f"同意关键词: {self.config.agree_keywords}")
        logger.info(f"拒绝关键词: {self.config.refuse_keywords}")

    async def _is_rejected(self, event: AstrMessageEvent) -> bool:
        user_id = extract_user_id(event)
        group_id = extract_group_id(event)

        if is_admin(user_id, self.config.admins):
            return False

        status = await self.storage.get_state(user_id, group_id)
        return status == AgreementState.REFUSED

    # ==================== 消息处理 ====================

    @filter.regex(r".*")
    async def on_message(self, event: AstrMessageEvent):
        msg = event.message_str

        # 第一步：优先处理命令（不受拒绝状态限制）
        try:
            if event.is_command():
                return
        except AttributeError:
            if msg.startswith("/") or msg.startswith("#"):
                return

        # 第二步：非命令消息检查拒绝状态
        if await self._is_rejected(event):
            event.stop_event()
            return

        # 第三步：处理普通消息
        await self.message_handler.handle(event)

    # ==================== 命令处理 ====================

    @filter.command("doc_stats")
    async def cmd_stats(self, event: AstrMessageEvent):
        await self.command_handler.cmd_stats(event)

    @filter.command("doc_status")
    async def cmd_status(self, event: AstrMessageEvent):
        await self.command_handler.cmd_status(event)

    @filter.command("doc_undo")
    async def cmd_undo(self, event: AstrMessageEvent):
        await self.command_handler.cmd_undo(event)

    @filter.command("doc_help")
    async def cmd_help(self, event: AstrMessageEvent):
        await self.command_handler.cmd_help(event)

    @filter.command("doc_list")
    async def cmd_list(self, event: AstrMessageEvent):
        await self.command_handler.cmd_list(event)

    @filter.command("doc_reset")
    async def cmd_reset(self, event: AstrMessageEvent):
        await self.command_handler.cmd_reset(event)

    @filter.command("doc_reset_user")
    async def cmd_reset_user(self, event: AstrMessageEvent, user_id: str = ""):
        await self.command_handler.cmd_reset_user(event, user_id)

    @filter.command("doc_reload")
    async def cmd_reload(self, event: AstrMessageEvent):
        await self.command_handler.cmd_reload(event)

    async def terminate(self):
        logger.info("文档签订插件已终止")
