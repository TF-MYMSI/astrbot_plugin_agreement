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
        
        # 安全获取配置
        plugin_config = self._get_plugin_config(config)
        
        # 初始化存储
        self.storage = AgreementStorage(context)
        
        # 获取机器人QQ
        try:
            self.bot_qq = context.get_bot().qq
        except:
            self.bot_qq = ''
        
        # 初始化处理器
        self.message_handler = MessageHandler(plugin_config, self.storage, self.bot_qq)
        self.command_handler = CommandHandler(plugin_config, self.storage)
        
        logger.info("文档签订插件已加载")
    
    def _get_plugin_config(self, raw_config):
        """将原始配置转换为 PluginConfig 对象"""
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
        return PluginConfig(raw_config)
    
    async def on_message(self, event: AstrMessageEvent):
        """统一入口：先判断命令，再处理协议"""
        try:
            msg = event.message_str.strip()
            
            # ========== 命令路由（优先处理） ==========
            # 用户命令
            if msg == '/doc_stats':
                async for result in self.command_handler.cmd_stats(event):
                    yield result
                return
            
            if msg == '/doc_status':
                async for result in self.command_handler.cmd_status(event):
                    yield result
                return
            
            if msg == '/doc_undo':
                async for result in self.command_handler.cmd_undo(event):
                    yield result
                return
            
            if msg == '/doc_help':
                async for result in self.command_handler.cmd_help(event):
                    yield result
                return
            
            # 管理员命令
            if msg == '/doc_list':
                async for result in self.command_handler.cmd_list(event):
                    yield result
                return
            
            if msg == '/doc_reset':
                async for result in self.command_handler.cmd_reset(event):
                    yield result
                return
            
            if msg == '/doc_reload':
                async for result in self.command_handler.cmd_reload(event):
                    yield result
                return
            
            if msg.startswith('/doc_reset_user'):
                parts = msg.split()
                target = parts[1] if len(parts) > 1 else ""
                async for result in self.command_handler.cmd_reset_user(event, target):
                    yield result
                return
            
            # ========== 不是命令，交给协议处理器 ==========
            async for result in self.message_handler.handle(event):
                if result:
                    yield result
                    
        except Exception as e:
            logger.error(f"消息处理出错: {e}")
            import traceback
            traceback.print_exc()
    
    async def terminate(self):
        logger.info("文档签订插件已卸载")
