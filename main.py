import json
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .core import PluginConfig, AgreementStorage
from .handlers import MessageHandler, CommandHandler

@register("astrbot_plugin_agreement", "TF-MYMSI", "文档签订插件", "1.0.0")
class AgreementPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        
        # 安全获取配置
        plugin_config = self._get_plugin_config(config)
        
        # 初始化存储
        self.storage = AgreementStorage(context)
        
        # ========== 获取机器人QQ ==========
        # 优先从配置读取
        self.bot_qq = plugin_config.bot_qq if hasattr(plugin_config, 'bot_qq') and plugin_config.bot_qq else ''
        
        # 如果配置中没有，尝试自动获取
        if not self.bot_qq:
            try:
                if hasattr(context, 'get_bot'):
                    bot = context.get_bot()
                    if bot and hasattr(bot, 'qq'):
                        self.bot_qq = str(bot.qq)
                        logger.info(f"自动获取 bot_qq={self.bot_qq}")
            except Exception as e:
                logger.debug(f"自动获取 bot_qq 失败: {e}")
        
        # 如果还是空，记录警告
        if not self.bot_qq:
            logger.warning("未能获取到 bot_qq，群聊@检测将无法正常工作！请在 WebUI 中配置 bot_qq")
        
        logger.info(f"最终 bot_qq={self.bot_qq}")
        
        # 初始化处理器
        self.message_handler = MessageHandler(plugin_config, self.storage, self.bot_qq)
        self.command_handler = CommandHandler(plugin_config, self.storage)
        
        logger.info("文档签订插件已加载")
    
    def _get_plugin_config(self, raw_config):
        if raw_config is None:
            raw_config = {}
        if isinstance(raw_config, str):
            try:
                raw_config = json.loads(raw_config)
            except json.JSONDecodeError:
                raw_config = {}
        if isinstance(raw_config, dict) and 'config' in raw_config:
            raw_config = raw_config['config']
        if not isinstance(raw_config, dict):
            raw_config = {}
        
        # 调试：打印配置内容
        logger.info(f"配置内容中的 bot_qq: {raw_config.get('bot_qq', '未设置')}")
        
        return PluginConfig(raw_config)
    
    # ========== 命令处理 ==========
    @filter.command("doc_stats")
    async def doc_stats(self, event: AstrMessageEvent):
        async for result in self.command_handler.cmd_stats(event):
            yield result
    
    @filter.command("doc_status")
    async def doc_status(self, event: AstrMessageEvent):
        async for result in self.command_handler.cmd_status(event):
            yield result
    
    @filter.command("doc_undo")
    async def doc_undo(self, event: AstrMessageEvent):
        async for result in self.command_handler.cmd_undo(event):
            yield result
    
    @filter.command("doc_help")
    async def doc_help(self, event: AstrMessageEvent):
        async for result in self.command_handler.cmd_help(event):
            yield result
    
    @filter.command("doc_list")
    async def doc_list(self, event: AstrMessageEvent):
        async for result in self.command_handler.cmd_list(event):
            yield result
    
    @filter.command("doc_reset")
    async def doc_reset(self, event: AstrMessageEvent):
        async for result in self.command_handler.cmd_reset(event):
            yield result
    
    @filter.command("doc_reset_user")
    async def doc_reset_user(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        parts = msg.split()
        target = parts[1] if len(parts) > 1 else ""
        async for result in self.command_handler.cmd_reset_user(event, target):
            yield result
    
    @filter.command("doc_reload")
    async def doc_reload(self, event: AstrMessageEvent):
        async for result in self.command_handler.cmd_reload(event):
            yield result
    
    # ========== 普通消息处理（协议签订） ==========
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def handle_agreement(self, event: AstrMessageEvent):
        """处理所有普通消息（协议签订流程）"""
        try:
            msg = event.message_str.strip()
            
            # 跳过命令消息
            if msg.startswith('doc_'):
                return
            
            async for result in self.message_handler.handle(event):
                if result:
                    yield result
        except Exception as e:
            logger.error(f"协议处理出错: {e}")
            import traceback
            traceback.print_exc()
    
    async def terminate(self):
        logger.info("文档签订插件已卸载")
