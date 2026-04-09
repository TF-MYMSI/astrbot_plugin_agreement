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
        
        # 安全获取配置并转换为 PluginConfig 对象
        plugin_config = self._get_plugin_config(config)
        
        # 初始化存储
        self.storage = AgreementStorage(context)
        
        # 获取机器人QQ
        self.bot_qq = context.get_bot().qq if hasattr(context, 'get_bot') else ''
        
        # 初始化处理器（传入 PluginConfig 对象）
        self.message_handler = MessageHandler(plugin_config, self.storage, self.bot_qq)
        self.command_handler = CommandHandler(plugin_config, self.storage, context)
        
        logger.info("文档签订插件已加载")
    
    def _get_plugin_config(self, raw_config):
        """将原始配置转换为 PluginConfig 对象"""
        # 处理字符串类型
        if isinstance(raw_config, str):
            try:
                raw_config = json.loads(raw_config)
            except json.JSONDecodeError:
                raw_config = {}
        
        # 处理 None
        if raw_config is None:
            raw_config = {}
        
        # 处理嵌套结构（AstrBot 可能传入 {"config": {...}}）
        if isinstance(raw_config, dict) and 'config' in raw_config:
            raw_config = raw_config['config']
        
        # 确保是字典
        if not isinstance(raw_config, dict):
            raw_config = {}
        
        # 创建 PluginConfig 对象
        return PluginConfig(raw_config)
    
    async def on_message(self, event: AstrMessageEvent):
        """处理消息"""
        try:
            async for result in self.message_handler.handle(event):
                yield result
        except Exception as e:
            logger.error(f"消息处理出错: {e}")
    
    async def terminate(self):
        """插件卸载时清理"""
        logger.info("文档签订插件已卸载")
