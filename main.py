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
        
        # ========== 获取机器人QQ（多种方式尝试） ==========
        self.bot_qq = self._get_bot_qq(context, plugin_config)
        logger.info(f"最终获取到 bot_qq={self.bot_qq}")
        
        # 初始化处理器
        self.message_handler = MessageHandler(plugin_config, self.storage, self.bot_qq)
        self.command_handler = CommandHandler(plugin_config, self.storage)
        
        logger.info("文档签订插件已加载")
    
    def _get_bot_qq(self, context, plugin_config):
        """获取机器人QQ号，多种方式尝试"""
        bot_qq = None
        
        # 方法1：从配置文件中读取
        if hasattr(plugin_config, 'bot_qq') and plugin_config.bot_qq:
            bot_qq = str(plugin_config.bot_qq)
            logger.info(f"从配置文件获取 bot_qq={bot_qq}")
            return bot_qq
        
        # 方法2：从 context.get_bot() 获取
        try:
            if hasattr(context, 'get_bot'):
                bot = context.get_bot()
                if bot:
                    if hasattr(bot, 'qq'):
                        bot_qq = str(bot.qq)
                        logger.info(f"从 context.get_bot().qq 获取 bot_qq={bot_qq}")
                        return bot_qq
                    elif hasattr(bot, 'uin'):
                        bot_qq = str(bot.uin)
                        logger.info(f"从 context.get_bot().uin 获取 bot_qq={bot_qq}")
                        return bot_qq
        except Exception as e:
            logger.debug(f"从 context.get_bot() 获取失败: {e}")
        
        # 方法3：从 context 直接获取
        try:
            if hasattr(context, 'bot_qq'):
                bot_qq = str(context.bot_qq)
                logger.info(f"从 context.bot_qq 获取 bot_qq={bot_qq}")
                return bot_qq
            if hasattr(context, 'self_qq'):
                bot_qq = str(context.self_qq)
                logger.info(f"从 context.self_qq 获取 bot_qq={bot_qq}")
                return bot_qq
            if hasattr(context, 'uin'):
                bot_qq = str(context.uin)
                logger.info(f"从 context.uin 获取 bot_qq={bot_qq}")
                return bot_qq
        except Exception as e:
            logger.debug(f"从 context 属性获取失败: {e}")
        
        # 方法4：从 event 中获取（需要在消息处理时才能获取，这里先返回空）
        logger.warning("无法自动获取 bot_qq，将在消息处理时尝试从 event 获取")
        return ""
    
    def _get_bot_qq_from_event(self, event: AstrMessageEvent):
        """从消息事件中获取机器人QQ"""
        try:
            # 尝试从 event 中获取
            if hasattr(event, 'self_id'):
                return str(event.self_id)
            if hasattr(event, 'bot_qq'):
                return str(event.bot_qq)
            if hasattr(event, 'robot_qq'):
                return str(event.robot_qq)
            
            # 尝试从 adapter 获取
            if hasattr(event, 'adapter') and hasattr(event.adapter, 'bot_qq'):
                return str(event.adapter.bot_qq)
        except Exception as e:
            logger.debug(f"从 event 获取 bot_qq 失败: {e}")
        return None
    
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
        logger.info(f"[MAIN] handle_agreement 被调用, 消息={event.message_str}")
        
        try:
            # 如果 bot_qq 为空，尝试从 event 获取
            if not self.bot_qq:
                bot_qq_from_event = self._get_bot_qq_from_event(event)
                if bot_qq_from_event:
                    self.bot_qq = bot_qq_from_event
                    # 更新 message_handler 中的 bot_qq
                    self.message_handler.bot_qq = self.bot_qq
                    logger.info(f"从 event 获取到 bot_qq={self.bot_qq}")
            
            msg = event.message_str.strip()
            
            # 跳过命令消息
            if msg.startswith('doc_'):
                logger.info(f"[MAIN] 跳过命令: {msg}")
                return
            
            logger.info(f"[MAIN] 调用 message_handler.handle")
            async for result in self.message_handler.handle(event):
                if result:
                    logger.info(f"[MAIN] 得到回复，yield")
                    yield result
                else:
                    logger.info(f"[MAIN] 无回复")
        except Exception as e:
            logger.error(f"[MAIN] 协议处理出错: {e}")
            import traceback
            traceback.print_exc()
    
    async def terminate(self):
        logger.info("文档签订插件已卸载")
