"""配置管理"""

from typing import List, Dict, Any
from astrbot.api import AstrBotConfig


class PluginConfig:
    """插件配置封装"""

    def __init__(self, config: AstrBotConfig):
        self._cfg = config

    # ==================== 基础配置 ====================
    @property
    def admins(self) -> List[str]:
        val = self._cfg.get("管理员列表", [])
        return val if isinstance(val, list) else []

    @property
    def scope_private(self) -> bool:
        val = self._cfg.get("启用私聊", True)
        return bool(val)

    @property
    def scope_group(self) -> bool:
        val = self._cfg.get("启用群聊", False)
        return bool(val)

    # ==================== 文档配置 ====================
    @property
    def doc_name(self) -> str:
        return str(self._cfg.get("文档名称", "用户协议"))

    @property
    def doc_version(self) -> str:
        return str(self._cfg.get("文档版本", "v1.0"))

    @property
    def doc_updated(self) -> str:
        return str(self._cfg.get("更新日期", "2026-04-09"))

    @property
    def doc_contact(self) -> str:
        return str(self._cfg.get("联系方式", "QQ群 000000000"))

    @property
    def sections(self) -> List[Dict[str, str]]:
        sections = self._cfg.get("文档章节", [])
        
        # 如果 sections 不是列表，返回空列表
        if not isinstance(sections, list):
            return []
        
        result = []
        for s in sections:
            # 如果是字典，正常处理
            if isinstance(s, dict):
                result.append({
                    "title": s.get("标题", ""),
                    "content": s.get("内容", "")
                })
            # 如果是字符串，跳过（可能是错误的配置格式）
            elif isinstance(s, str):
                continue
            # 其他类型也跳过
            else:
                continue
        return result

    # ==================== 触发配置 ====================
    @property
    def trigger_keywords(self) -> List[str]:
        val = self._cfg.get("触发关键词", ["协议", "规则", "条例"])
        return val if isinstance(val, list) else ["协议", "规则", "条例"]

    @property
    def agree_keywords(self) -> List[str]:
        val = self._cfg.get("同意关键词", ["同意", "agree", "YES", "是", "接受"])
        return val if isinstance(val, list) else ["同意", "agree", "YES", "是", "接受"]

    @property
    def refuse_keywords(self) -> List[str]:
        val = self._cfg.get("拒绝关键词", ["不同意", "disagree", "NO", "否", "拒绝"])
        return val if isinstance(val, list) else ["不同意", "disagree", "NO", "否", "拒绝"]

    @property
    def cooldown_seconds(self) -> int:
        val = self._cfg.get("冷却时间", 30)
        return int(val) if val else 30

    @property
    def delivery_text(self) -> bool:
        val = self._cfg.get("发送文字协议", True)
        return bool(val)

    # ==================== 回复配置 ====================
    @property
    def reply_agree(self) -> str:
        return str(self._cfg.get("同意后回复", "✅ 已记录你的同意。现在可以正常使用本机器人。"))

    @property
    def reply_refuse(self) -> str:
        return str(self._cfg.get("拒绝后回复", "❌ 已记录你的拒绝。本机器人将无法为你服务。"))

    @property
    def reply_waiting(self) -> str:
        return str(self._cfg.get("等待时回复", "📝 请回复「同意」或「不同意」接受{name}。"))

    # ==================== 反悔配置 ====================
    @property
    def allow_undo(self) -> bool:
        val = self._cfg.get("允许反悔", True)
        return bool(val)

    @property
    def max_undo(self) -> int:
        val = self._cfg.get("最大反悔次数", 3)
        return int(val) if val else 3

    @property
    def undo_cooldown(self) -> int:
        val = self._cfg.get("反悔冷却时间", 86400)
        return int(val) if val else 86400

    # ==================== 辅助方法 ====================
    def format_reply(self, template: str) -> str:
        return template.replace("{name}", self.doc_name)

    def build_document(self) -> str:
        if not self.delivery_text:
            return ""

        lines = [
            f"{self.doc_name}",
            "",
            f"版本：{self.doc_version}",
            f"更新日期：{self.doc_updated}",
            f"联系方式：{self.doc_contact}",
            ""
        ]
        for section in self.sections:
            title = section.get("title", "")
            content = section.get("content", "")
            if title or content:
                lines.extend([title, content, ""])
        return "\n".join(lines).strip()
