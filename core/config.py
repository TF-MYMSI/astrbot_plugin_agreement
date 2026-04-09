"""配置管理"""

import re
from typing import List, Dict, Any


class PluginConfig:
    """插件配置类"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        # 管理员配置
        self.admins = config_dict.get('管理员列表', [])
        
        # 作用范围
        self.scope_private = config_dict.get('启用私聊', True)
        self.scope_group = config_dict.get('启用群聊', False)
        
        # 文档配置
        self.doc_name = config_dict.get('文档名称', '用户协议')
        self.doc_version = config_dict.get('文档版本', 'v1.0')
        self.doc_updated = config_dict.get('更新日期', '2026-04-09')
        self.contact = config_dict.get('联系方式', 'QQ群 000000000')
        
        # 关键词配置
        self.trigger_keywords = config_dict.get('触发关键词', ['协议', '规则', '条例'])
        self.agree_keywords = config_dict.get('同意关键词', ['同意', 'agree', 'YES', '是', '接受'])
        self.refuse_keywords = config_dict.get('拒绝关键词', ['不同意', 'disagree', 'NO', '否', '拒绝'])
        
        # 冷却配置
        self.cooldown_seconds = config_dict.get('冷却时间', 30)
        
        # 发送配置
        self.send_text = config_dict.get('发送文字协议', True)
        
        # 回复文案
        self.reply_agree = config_dict.get('同意后回复', '✅ 已记录你的同意。现在可以正常使用本机器人。')
        self.reply_refuse = config_dict.get('拒绝后回复', '❌ 已记录你的拒绝。本机器人将无法为你服务。')
        self.reply_waiting = config_dict.get('等待时回复', '📝 请回复「同意」或「不同意」接受{name}。')
        
        # 文档章节
        self.doc_sections = config_dict.get('文档章节', [])
        
        # 反悔机制
        self.allow_undo = config_dict.get('允许反悔', True)
        self.max_undo = config_dict.get('最大反悔次数', 3)
        self.undo_cooldown = config_dict.get('反悔冷却时间', 86400)
        
        # ========== 机器人QQ（用于检测@） ==========
        self.bot_qq = config_dict.get('bot_qq', '')
    
    def build_document(self) -> str:
        """构建协议文档"""
        if self.doc_sections:
            # 使用章节构建文档
            sections_text = []
            for section in self.doc_sections:
                title = section.get('标题', '')
                content = section.get('内容', '')
                if title and content:
                    sections_text.append(f"【{title}】\n{content}")
                elif content:
                    sections_text.append(content)
            
            doc = f"【{self.doc_name}】{self.doc_version}\n\n"
            doc += "\n\n".join(sections_text)
            doc += f"\n\n更新日期：{self.doc_updated}\n联系方式：{self.contact}"
            return doc
        else:
            # 默认文档
            return f"【{self.doc_name}】{self.doc_version}\n\n请仔细阅读以下协议内容。\n\n更新日期：{self.doc_updated}\n联系方式：{self.contact}"
    
    def format_reply(self, reply: str) -> str:
        """格式化回复"""
        if not reply:
            return ""
        return reply.replace("{name}", self.doc_name)
