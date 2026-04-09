import json
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .handlers.message_handler import MessageHandler

@register("astrbot_plugin_agreement", "Your Name", "文档签订插件", "1.0.0")
class AgreementPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        
        # 规范化配置
        self.config = self._normalize_config(config)
        self.message_handler = MessageHandler(self)
        
        # 注册命令
        self.register_commands()
    
    def _normalize_config(self, config):
        """将配置统一转换为字典格式"""
        if config is None:
            return {}
        if isinstance(config, str):
            try:
                return json.loads(config)
            except json.JSONDecodeError:
                logger.error(f"解析配置JSON失败: {config}")
                return {}
        return config if isinstance(config, dict) else {}
    
    def reload_config(self, config: dict = None):
        """重载配置"""
        self.config = self._normalize_config(config)
        if hasattr(self.message_handler, '_ensure_config_dict'):
            self.message_handler._ensure_config_dict()
        logger.info("文档签订插件配置已重载")
    
    def register_commands(self):
        """注册命令"""
        # /doc_status - 查看个人状态
        @self.context.register_command("doc_status", "查看协议签订状态")
        async def doc_status(event: AstrMessageEvent):
            async for result in self.message_handler.get_status(event):
                yield result
        
        # /doc_undo - 反悔重签
        @self.context.register_command("doc_undo", "反悔重新签订协议")
        async def doc_undo(event: AstrMessageEvent):
            async for result in self.message_handler.undo(event):
                yield result
    
    async def on_message(self, event: AstrMessageEvent):
        """处理消息"""
        async for result in self.message_handler.on_message(event):
            yield result
    
    async def terminate(self):
        """插件卸载时的清理"""
        pass
