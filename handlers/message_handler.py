import json
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Plain

class MessageHandler:
    def __init__(self, plugin):
        self.plugin = plugin
        self._ensure_config_dict()
    
    def _ensure_config_dict(self):
        """确保配置是字典格式"""
        if hasattr(self.plugin, 'config'):
            config = self.plugin.config
            if isinstance(config, str):
                try:
                    self.plugin.config = json.loads(config)
                except json.JSONDecodeError:
                    self.plugin.config = {}
            elif not isinstance(config, dict):
                self.plugin.config = {}
    
    def _get_config_value(self, key, default=''):
        """安全获取配置值"""
        self._ensure_config_dict()
        config = self.plugin.config if hasattr(self.plugin, 'config') else {}
        if not isinstance(config, dict):
            config = {}
        return config.get(key, default)
    
    async def on_message(self, event: AstrMessageEvent):
        """处理消息"""
        # 确保配置是字典格式
        self._ensure_config_dict()
        
        # 获取消息文本
        message_text = event.message_str.strip()
        
        # 获取配置
        trigger_word = self._get_config_value('trigger_word', '/agreement')
        agree_word = self._get_config_value('agree_word', '同意')
        disagree_word = self._get_config_value('disagree_word', '不同意')
        agreement_content = self._get_config_value('agreement_content', '请阅读协议内容\n回复「同意」表示接受，回复「不同意」表示拒绝。')
        
        # 获取用户信息
        user_id = str(event.get_sender_id())
        platform = event.platform_name
        
        # 检查是否在签订流程中
        session_key = f"agreement_session_{platform}_{user_id}"
        in_session = self.plugin.context.get(session_key, False)
        
        # 如果用户在签订流程中
        if in_session:
            if message_text == agree_word:
                # 用户同意
                status_key = f"agreement_status_{platform}_{user_id}"
                self.plugin.context.set(status_key, {
                    'status': 'agreed',
                    'timestamp': event.get_time(),
                    'agreement_content': agreement_content
                })
                self.plugin.context.set(session_key, False)
                
                # 发送同意回复
                reply_text = self._get_config_value('agree_reply', '您已同意协议，感谢您的配合！')
                yield event.reply(Plain(reply_text))
                
            elif message_text == disagree_word:
                # 用户拒绝
                status_key = f"agreement_status_{platform}_{user_id}"
                self.plugin.context.set(status_key, {
                    'status': 'disagreed',
                    'timestamp': event.get_time()
                })
                self.plugin.context.set(session_key, False)
                
                # 发送拒绝回复（如果配置了）
                disagree_reply = self._get_config_value('disagree_reply', '')
                if disagree_reply:
                    yield event.reply(Plain(disagree_reply))
            else:
                # 无效输入，重新发送协议
                yield event.reply(Plain(agreement_content))
                yield event.reply(Plain(f'请回复「{agree_word}」或「{disagree_word}」'))
            return
        
        # 检查是否触发协议签订
        if message_text == trigger_word:
            # 检查用户是否已经同意过
            status_key = f"agreement_status_{platform}_{user_id}"
            status = self.plugin.context.get(status_key, {})
            
            if isinstance(status, dict) and status.get('status') == 'agreed':
                # 已经同意过
                already_agreed_reply = self._get_config_value('already_agreed_reply', '您已经同意过协议了，无需重复签订。')
                yield event.reply(Plain(already_agreed_reply))
                return
            
            # 开始签订流程
            self.plugin.context.set(session_key, True)
            yield event.reply(Plain(agreement_content))
            yield event.reply(Plain(f'请回复「{agree_word}」表示同意，回复「{disagree_word}」表示拒绝。'))
            return
    
    async def get_status(self, event: AstrMessageEvent):
        """查看个人状态"""
        user_id = str(event.get_sender_id())
        platform = event.platform_name
        status_key = f"agreement_status_{platform}_{user_id}"
        status = self.plugin.context.get(status_key, {})
        
        if isinstance(status, dict) and status.get('status') == 'agreed':
            yield event.reply(Plain("您已经同意过协议。"))
        elif isinstance(status, dict) and status.get('status') == 'disagreed':
            yield event.reply(Plain("您之前拒绝了协议。"))
        else:
            yield event.reply(Plain("您尚未签订协议。"))
    
    async def undo(self, event: AstrMessageEvent):
        """反悔重签"""
        user_id = str(event.get_sender_id())
        platform = event.platform_name
        status_key = f"agreement_status_{platform}_{user_id}"
        
        # 清除状态
        self.plugin.context.set(status_key, {})
        
        # 清除会话状态
        session_key = f"agreement_session_{platform}_{user_id}"
        self.plugin.context.set(session_key, False)
        
        yield event.reply(Plain("已清除您的协议状态，您可以重新签订。"))
