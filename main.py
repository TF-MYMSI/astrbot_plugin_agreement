import json
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .core import PluginConfig, AgreementStorage
from .handlers import MessageHandler, CommandHandler

@register("astrbot_plugin_agreement", "TF-MYMSI", "文档签订插件", "1.0.0")
class AgreementPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        
        plugin_config = self._get_plugin_config(config)
        self.storage = AgreementStorage(context)
        
        try:
            self.bot_qq = context.get_bot().qq
        except:
            self.bot_qq = ''
        
        self.message_handler = MessageHandler(plugin_config, self.storage, self.bot_qq)
        self.command_handler = CommandHandler(plugin_config, self.storage, context)
        
        logger.info("文档签订插件已加载")
    
    def _get_plugin_config(self, raw_config):
        if raw_config is None:
            raw_config = {}
        if isinstance(raw_config, str):
            try:
                raw_config = json.loads(raw_config)
            except:
                raw_config = {}
        if isinstance(raw_config, dict) and 'config' in raw_config:
            raw_config = raw_config['config']
        if not isinstance(raw_config, dict):
            raw_config = {}
        return PluginConfig(raw_config)
    
    async def on_message(self, event: AstrMessageEvent):
        try:
            msg = event.message_str.strip()
            
            # 命令处理
            if msg == '/doc_status':
                async for r in self.command_handler.cmd_status(event):
                    yield r
            elif msg == '/doc_undo':
                async for r in self.command_handler.cmd_undo(event):
                    yield r
            elif msg == '/doc_help':
                async for r in self.command_handler.cmd_help(event):
                    yield r
            elif msg == '/doc_stats':
                async for r in self.command_handler.cmd_stats(event):
                    yield r
            else:
                # 协议签订流程
                async for r in self.message_handler.handle(event):
                    if r:
                        yield r
        except Exception as e:
            logger.error(f"处理出错: {e}")
    
    async def terminate(self):
        logger.info("文档签订插件已卸载")
