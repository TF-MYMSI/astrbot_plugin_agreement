import json
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain

from .core import PluginConfig, AgreementStorage
from .handlers import MessageHandler

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
        
        # 初始化消息处理器（统一处理所有消息）
        self.message_handler = MessageHandler(plugin_config, self.storage, self.bot_qq)
        
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
        """统一处理所有消息（包括命令和协议签订）"""
        try:
            async for result in self.message_handler.handle(event):
                if result:
                    yield result
        except Exception as e:
            logger.error(f"消息处理出错: {e}")
            import traceback
            traceback.print_exc()
    
    async def terminate(self):
        logger.info("文档签订插件已卸载")
