import json
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.star.command import command

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
    
    # ========== 使用 @command 装饰器注册命令 ==========
    
    @command(command="doc_stats")
    async def doc_stats(self, event: AstrMessageEvent):
        """查看统计"""
        async for result in self.command_handler.cmd_stats(event):
            yield result
    
    @command(command="doc_status")
    async def doc_status(self, event: AstrMessageEvent):
        """查看个人状态"""
        async for result in self.command_handler.cmd_status(event):
            yield result
    
    @command(command="doc_undo")
    async def doc_undo(self, event: AstrMessageEvent):
        """反悔重签"""
        async for result in self.command_handler.cmd_undo(event):
            yield result
    
    @command(command="doc_help")
    async def doc_help(self, event: AstrMessageEvent):
        """帮助"""
        async for result in self.command_handler.cmd_help(event):
            yield result
    
    @command(command="doc_list")
    async def doc_list(self, event: AstrMessageEvent):
        """用户列表（管理员）"""
        async for result in self.command_handler.cmd_list(event):
            yield result
    
    @command(command="doc_reset")
    async def doc_reset(self, event: AstrMessageEvent):
        """重置统计（管理员）"""
        async for result in self.command_handler.cmd_reset(event):
            yield result
    
    @command(command="doc_reset_user")
    async def doc_reset_user(self, event: AstrMessageEvent):
        """重置指定用户（管理员）"""
        # 从消息中提取参数
        msg = event.message_str.strip()
        parts = msg.split()
        target = parts[1] if len(parts) > 1 else ""
        async for result in self.command_handler.cmd_reset_user(event, target):
            yield result
    
    @command(command="doc_reload")
    async def doc_reload(self, event: AstrMessageEvent):
        """重载配置（管理员）"""
        async for result in self.command_handler.cmd_reload(event):
            yield result
    
    # ========== 普通消息处理（协议签订） ==========
    
    async def on_message(self, event: AstrMessageEvent):
        """处理非命令的普通消息"""
        try:
            # 只处理协议签订流程，命令已经被 @command 拦截了
            async for result in self.message_handler.handle(event):
                if result:
                    yield result
        except Exception as e:
            logger.error(f"消息处理出错: {e}")
    
    async def terminate(self):
        logger.info("文档签订插件已卸载")
