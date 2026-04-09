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
        try:
            self.bot_qq = context.get_bot().qq
        except:
            self.bot_qq = ''
        
        # 初始化处理器
        self.message_handler = MessageHandler(plugin_config, self.storage, self.bot_qq)
        self.command_handler = CommandHandler(plugin_config, self.storage, context)
        
        # 注册命令
        self._register_commands()
        
        logger.info("文档签订插件已加载")
    
    def _get_plugin_config(self, raw_config):
        """将原始配置转换为 PluginConfig 对象"""
        # 处理 None
        if raw_config is None:
            raw_config = {}
        
        # 处理字符串类型（JSON）
        if isinstance(raw_config, str):
            try:
                raw_config = json.loads(raw_config)
            except json.JSONDecodeError as e:
                logger.error(f"解析配置JSON失败: {e}")
                raw_config = {}
        
        # 处理嵌套结构（AstrBot 可能传入 {"config": {...}}）
        if isinstance(raw_config, dict) and 'config' in raw_config:
            raw_config = raw_config['config']
        
        # 确保是字典
        if not isinstance(raw_config, dict):
            logger.error(f"配置格式错误，应为字典，实际为: {type(raw_config)}")
            raw_config = {}
        
        # 创建 PluginConfig 对象
        return PluginConfig(raw_config)
    
    def _register_commands(self):
        """注册命令"""
        # /doc_status - 查看个人状态
        @self.context.register_command("doc_status", "查看协议签订状态")
        async def doc_status(event: AstrMessageEvent):
            async for result in self.command_handler.cmd_status(event):
                yield result
        
        # /doc_undo - 反悔重签
        @self.context.register_command("doc_undo", "反悔重新签订协议")
        async def doc_undo(event: AstrMessageEvent):
            async for result in self.command_handler.cmd_undo(event):
                yield result
        
        # /doc_help - 帮助
        @self.context.register_command("doc_help", "查看帮助")
        async def doc_help(event: AstrMessageEvent):
            async for result in self.command_handler.cmd_help(event):
                yield result
        
        # /doc_stats - 统计（如果有）
        @self.context.register_command("doc_stats", "查看统计")
        async def doc_stats(event: AstrMessageEvent):
            async for result in self.command_handler.cmd_stats(event):
                yield result
    
    async def on_message(self, event: AstrMessageEvent):
        """处理消息"""
        try:
            async for result in self.message_handler.handle(event):
                if result:
                    yield result
        except Exception as e:
            logger.error(f"消息处理出错: {e}")
    
    async def terminate(self):
        """插件卸载时清理"""
        logger.info("文档签订插件已卸载")
