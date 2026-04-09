"""配置管理"""

from typing import List, Dict
from astrbot.api import AstrBotConfig


class PluginConfig:
    """插件配置封装"""

    def __init__(self, config: AstrBotConfig):
        self._cfg = config

    # ==================== 基础配置 ====================
    @property
    def admins(self) -> List[str]:
        val = self._cfg.get("admins", [])
        return val if isinstance(val, list) else []

    @property
    def scope_private(self) -> bool:
        return bool(self._cfg.get("scope_private", True))

    @property
    def scope_group(self) -> bool:
        return bool(self._cfg.get("scope_group", False))

    # ==================== 文档配置 ====================
    @property
    def doc_name(self) -> str:
        return str(self._cfg.get("doc_name", "用户协议"))

    @property
    def doc_version(self) -> str:
        return str(self._cfg.get("doc_version", "v1.0"))

    @property
    def doc_updated(self) -> str:
        return str(self._cfg.get("doc_updated", "2026-04-09"))

    @property
    def doc_contact(self) -> str:
        return str(self._cfg.get("doc_contact", "QQ群 000000000"))

    @property
    def sections(self) -> List[Dict[str, str]]:
        sections = self._cfg.get("doc_sections", [])
        if not isinstance(sections, list):
            return []
        result = []
        for s in sections:
            if isinstance(s, dict):
                result.append({
                    "title": s.get("title", ""),
                    "content": s.get("content", "")
                })
        return result

    # ==================== 触发配置 ====================
    @property
    def trigger_keywords(self) -> List[str]:
        val = self._cfg.get("trigger_keywords", ["协议", "规则", "条例"])
        return val if isinstance(val, list) else ["协议", "规则", "条例"]

    @property
    def agree_keywords(self) -> List[str]:
        val = self._cfg.get("agree_keywords", ["同意", "agree", "YES", "是", "接受"])
        return val if isinstance(val, list) else ["同意", "agree", "YES", "是", "接受"]

    @property
    def refuse_keywords(self) -> List[str]:
        val = self._cfg.get("refuse_keywords", ["不同意", "disagree", "NO", "否", "拒绝"])
        return val if isinstance(val, list) else ["不同意", "disagree", "NO", "否", "拒绝"]

    @property
    def cooldown_seconds(self) -> int:
        return int(self._cfg.get("cooldown_seconds", 30))

    @property
    def delivery_text(self) -> bool:
        return bool(self._cfg.get("delivery_text", True))

    # ==================== 回复配置 ====================
    @property
    def reply_agree(self) -> str:
        return str(self._cfg.get("reply_agree", "✅ 已记录你的同意。现在可以正常使用本机器人。"))

    @property
    def reply_refuse(self) -> str:
        return str(self._cfg.get("reply_refuse", "❌ 已记录你的拒绝。本机器人将无法为你服务。"))

    @property
    def reply_waiting(self) -> str:
        return str(self._cfg.get("reply_waiting", "📝 请回复「同意」或「不同意」接受{name}。"))

    # ==================== 反悔配置 ====================
    @property
    def allow_undo(self) -> bool:
        return bool(self._cfg.get("allow_undo", True))

    @property
    def max_undo(self) -> int:
        return int(self._cfg.get("max_undo", 3))

    @property
    def undo_cooldown(self) -> int:
        return int(self._cfg.get("undo_cooldown", 86400))

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
