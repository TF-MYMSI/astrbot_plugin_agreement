import json
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .handlers.message_handler import MessageHandler

@register("astrbot_plugin_agreement", "TF-MYMSI", "文档签订插件", "1.0.0")
class AgreementPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        
        # 先规范化 config 参数
        normalized_config = self._normalize_config(config)
        # 如果 config 是字典且包含 'config' 键，则取其值；否则直接用
        if isinstance(normalized_config, dict) and 'config' in normalized_config:
            self.config = self._normalize_config(normalized_config.get('config', {}))
        else:
            self.config = normalized_config
        
        self.message_handler = MessageHandler(self)
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
        normalized_config = self._normalize_config(config)
        if isinstance(normalized_config, dict) and 'config' in normalized_config:
            self.config = self._normalize_config(normalized_config.get('config', {}))
        else:
            self.config = normalized_config
        
        if hasattr(self.message_handler, '_ensure_config_dict'):
            self.message_handler._ensure_config_dict()
        logger.info("文档签订插件配置已重载")
    
    def register_commands(self):
        """注册命令"""
        @self.context.register_command("doc_status", "查看协议签订状态")
        async def doc_status(event: AstrMessageEvent):
            async for result in self.message_handler.get_status(event):
                yield result
        
        @self.context.register_command("doc_undo", "反悔重新签订协议")
        async def doc_undo(event: AstrMessageEvent):
            async for result in self.message_handler.undo(event):
                yield result
        
        @self.context.register_command("doc_help", "查看帮助")
        async def doc_help(event: AstrMessageEvent):
            help_text = """文档签订插件帮助：
/doc_status - 查看个人签订状态
/doc_undo - 反悔重新签订协议
/doc_help - 显示本帮助
触发词可自定义，默认为 /agreement"""
            yield event.reply(Plain(help_text))
    
    async def on_message(self, event: AstrMessageEvent):
        """处理消息"""
        async for result in self.message_handler.on_message(event):
            yield result
    
    async def terminate(self):
        """插件卸载时的清理"""
        pass
