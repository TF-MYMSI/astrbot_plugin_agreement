import asyncio
"""
文档签订插件 - 用户协议/规则签订插件
首次触发关键词时发送文档（文字/图片），记录用户同意/拒绝状态
"""

from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Image, Plain
from astrbot.api import logger
import time
import os
import httpx
from typing import Optional, List, Union


@register(
    "astrbot_plugin_agreement",
    "星恒梦落",
    "文档签订插件，首次触发关键词时发送文档（文字/图片），记录用户同意/拒绝状态",
    "1.0.0"
)
class AgreementPlugin(Star):
    """文档签订插件主类"""

    # 状态常量
    STATE_NONE = None
    STATE_WAITING = "waiting"
    STATE_AGREED = "yes"
    STATE_REFUSED = "no"

    def __init__(self, context: Context):
        super().__init__(context)
        self._load_config()
        self._log_config()

    # ==================== 配置加载 ====================

    def _load_config(self) -> None:
        """加载所有配置"""
        cfg = self.config
        
        # 管理员配置
        self.admins: list = cfg.get("admins", [])
        
        # 生效范围配置
        scope = cfg.get("scope", {})
        self.scope_private: bool = scope.get("private", True)
        self.scope_group: bool = scope.get("group", False)
        
        # 文档配置
        doc = cfg.get("document", {})
        self.doc_name: str = doc.get("name", "用户协议")
        self.doc_version: str = doc.get("version", "v1.0")
        self.doc_updated: str = doc.get("updated", "2026-04-06")
        self.doc_contact: str = doc.get("contact", "QQ群 752775661")
        
        # 触发配置
        trigger = cfg.get("trigger", {})
        self.trigger_keywords: list = trigger.get("keywords", ["协议", "规则", "条例"])
        self.cooldown_seconds: int = trigger.get("cooldown", 30)
        
        # 发送方式配置
        delivery = cfg.get("delivery", {})
        self.delivery_text: bool = delivery.get("text", True)
        self.delivery_image: bool = delivery.get("image", False)
        
        # 图片配置
        image_cfg = cfg.get("image", {})
        self.image_url: str = image_cfg.get("url", "")
        self.image_path: str = image_cfg.get("path", "")
        
        # 回复配置
        replies = cfg.get("replies", {})
        self.reply_agree: str = replies.get("agree", "已记录你的同意。现在可以正常使用本机器人。")
        self.reply_refuse: str = replies.get("refuse", "已记录你的拒绝。本机器人将无法为你服务。")
        self.reply_waiting: str = replies.get("waiting", "请回复「同意」或「不同意」接受{name}。")
        
        # 文档章节（仅文字协议使用）
        self.sections: list = cfg.get("sections", [])
        
        # 构建文字协议文本
        self.doc_text: str = self._build_document() if self.delivery_text else ""
        
        # 验证图片配置
        self._validate_image_config()

    def _validate_image_config(self) -> None:
        """验证图片配置"""
        if not self.delivery_image:
            return
        
        has_url = bool(self.image_url and self.image_url.strip())
        has_path = bool(self.image_path and os.path.exists(self.image_path))
        
        if not has_url and not has_path:
            logger.warning("图片协议已启用但未配置有效的图片URL或本地路径")
        elif has_url:
            logger.info(f"图片协议已配置：{self.image_url}")
        elif has_path:
            logger.info(f"图片协议已配置：{self.image_path}")

    def _log_config(self) -> None:
        """记录配置日志"""
        delivery_modes = []
        if self.delivery_text:
            delivery_modes.append("文字")
        if self.delivery_image:
            delivery_modes.append("图片")
        
        logger.info(f"文档插件已加载 | 私聊: {self.scope_private} | 群聊: {self.scope_group}")
        logger.info(f"文档名称: {self.doc_name} | 发送方式: {'+'.join(delivery_modes) if delivery_modes else '无'}")
        logger.info(f"触发词: {self.trigger_keywords} | 管理员: {self.admins if self.admins else '未设置'}")

    def _build_document(self) -> str:
        """构建文字协议文本"""
        lines = [
            f"星恒梦落{self.doc_name}",
            "",
            f"版本：{self.doc_version}",
            f"更新日期：{self.doc_updated}",
            f"联系方式：{self.doc_contact}",
            ""
        ]
        
        for section in self.sections:
            title = section.get("title", "")
            content = section.get("content", "")
            title = title.replace("协议", self.doc_name)
            content = content.replace("本协议", f"本{self.doc_name}")
            lines.extend([title, content, ""])
        
        return "\n".join(lines).strip()

    # ==================== 图片发送 ====================

    async def _send_image(self, event: AstrMessageEvent) -> None:
        """发送图片协议"""
        image_data = None
        
        # 优先使用网络图片
        if self.image_url and self.image_url.strip():
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(self.image_url)
                    if response.status_code == 200:
                        image_data = response.content
                        logger.info(f"成功加载网络图片: {self.image_url}")
                    else:
                        logger.error(f"加载网络图片失败: HTTP {response.status_code}")
            except Exception as e:
                logger.error(f"加载网络图片异常: {e}")
        
        # 降级使用本地图片
        if image_data is None and self.image_path and os.path.exists(self.image_path):
            try:
                with open(self.image_path, "rb") as f:
                    image_data = f.read()
                logger.info(f"成功加载本地图片: {self.image_path}")
            except Exception as e:
                logger.error(f"加载本地图片失败: {e}")
        
        if image_data:
            yield event.reply([Image.from_bytes(image_data)])
        else:
            # 图片加载失败，降级发送文字协议
            logger.warning("图片加载失败，降级发送文字协议")
            yield event.plain_result(self.doc_text if self.doc_text else "协议内容加载失败，请稍后重试。")

    async def _send_document(self, event: AstrMessageEvent) -> None:
        """根据配置发送文档（文字/图片）"""
        sent = False
        
        # 发送图片协议
        if self.delivery_image:
            async for result in self._send_image(event):
                yield result
                sent = True
        
        # 发送文字协议（可与图片同时发送）
        if self.delivery_text:
            if sent:
                # 如果已发送图片，稍作延迟再发送文字
                await asyncio.sleep(0.5)
            yield event.plain_result(self.doc_text)
            sent = True
        
        if not sent:
            yield event.plain_result("协议内容加载失败，请稍后重试。")

    # ==================== 工具方法 ====================

    def _format_reply(self, template: str) -> str:
        """格式化回复内容，替换变量"""
        return template.replace("{name}", self.doc_name)

    def _is_admin(self, uid: str) -> bool:
        """检查是否为管理员"""
        return uid in self.admins

    def _contains_keyword(self, text: str) -> bool:
        """检查文本是否包含触发关键词"""
        return any(kw in text for kw in self.trigger_keywords)

    def _get_session_key(self, event: AstrMessageEvent) -> str:
        """获取会话存储键"""
        msg_type = event.get_message_type()
        if msg_type == "private":
            return f"doc_agree_{event.get_sender_id()}"
        return f"doc_agree_{event.get_group_id()}_{event.get_sender_id()}"

    def _get_stat_key(self, event: AstrMessageEvent) -> str:
        """获取统计存储键"""
        msg_type = event.get_message_type()
        if msg_type == "private":
            return "doc_stat_private"
        return f"doc_stat_group_{event.get_group_id()}"

    def _should_process(self, event: AstrMessageEvent) -> bool:
        """检查是否应该处理该消息"""
        msg_type = event.get_message_type()
        if msg_type == "private" and not self.scope_private:
            return False
        if msg_type == "group" and not self.scope_group:
            return False
        return True

    # ==================== 统计方法 ====================

    async def _update_stat(self, stat_key: str, field: str, delta: int = 1) -> None:
        """更新统计数据"""
        key = f"{stat_key}_{field}"
        current = await self.get_kv_data(key, 0)
        await self.put_kv_data(key, current + delta)

    async def _get_stat(self, stat_key: str, field: str) -> int:
        """获取统计数据"""
        return await self.get_kv_data(f"{stat_key}_{field}", 0)

    async def _add_to_user_list(self, stat_key: str, uid: str) -> None:
        """添加用户到列表"""
        user_list = await self.get_kv_data(f"{stat_key}_users", [])
        if uid not in user_list:
            user_list.append(uid)
            await self.put_kv_data(f"{stat_key}_users", user_list)
            await self._update_stat(stat_key, "total")

    # ==================== 状态处理 ====================

    async def _handle_new_user(self, event: AstrMessageEvent, session: str, stat_key: str):
        """处理新用户"""
        if not self._contains_keyword(event.message_str):
            return None
        
        logger.info(f"用户 {event.get_sender_id()} 触发关键词")
        await self.put_kv_data(session, self.STATE_WAITING)
        await self.put_kv_data(f"{session}_last", time.time())
        await self._add_to_user_list(stat_key, event.get_sender_id())
        
        # 返回生成器，发送文档
        return self._send_document(event)

    async def _handle_waiting(self, event: AstrMessageEvent, session: str, stat_key: str) -> Optional[str]:
        """处理等待确认状态"""
        msg = event.message_str
        
        if "同意" in msg:
            logger.info(f"用户 {event.get_sender_id()} 同意文档")
            await self.put_kv_data(session, self.STATE_AGREED)
            await self.put_kv_data(f"{session}_time", time.time())
            await self._update_stat(stat_key, "agreed")
            return self._format_reply(self.reply_agree)
        
        if "不同意" in msg:
            logger.info(f"用户 {event.get_sender_id()} 拒绝文档")
            await self.put_kv_data(session, self.STATE_REFUSED)
            await self.put_kv_data(f"{session}_time", time.time())
            await self._update_stat(stat_key, "refused")
            return self._format_reply(self.reply_refuse)
        
        # 检查冷却
        last_sent = await self.get_kv_data(f"{session}_last", 0)
        if time.time() - last_sent < self.cooldown_seconds:
            return self._format_reply(self.reply_waiting)
        
        # 重新发送文档
        await self.put_kv_data(f"{session}_last", time.time())
        # 返回生成器，重新发送文档
        return self._send_document(event)

    # ==================== 消息处理 ====================

    async def on_message(self, event: AstrMessageEvent):
        """处理所有消息"""
        if not self._should_process(event):
            return
        
        # 检查是否有可用的发送方式
        if not self.delivery_text and not self.delivery_image:
            return
        
        session = self._get_session_key(event)
        stat_key = self._get_stat_key(event)
        status = await self.get_kv_data(session, None)
        
        try:
            if status is None:
                result = await self._handle_new_user(event, session, stat_key)
                if result:
                    async for r in result:
                        yield r
                    event.stop_event()
                    
            elif status == self.STATE_WAITING:
                result = await self._handle_waiting(event, session, stat_key)
                if result:
                    if isinstance(result, str):
                        yield event.plain_result(result)
                    else:
                        async for r in result:
                            yield r
                    event.stop_event()
                    
            elif status == self.STATE_REFUSED:
                event.stop_event()
                
        except Exception as e:
            logger.error(f"文档插件处理消息时出错: {e}")
            yield event.plain_result("处理消息时出现错误，请稍后再试。")
            event.stop_event()

    # ==================== 管理员命令 ====================

    @register.command("doc_stats")
    async def cmd_stats(self, event: AstrMessageEvent):
        """查看文档签订统计"""
        stat_key = self._get_stat_key(event)
        msg_type = "私聊" if event.get_message_type() == "private" else "本群"
        
        total = await self._get_stat(stat_key, "total")
        agreed = await self._get_stat(stat_key, "agreed")
        refused = await self._get_stat(stat_key, "refused")
        waiting = total - agreed - refused
        rate = (agreed / total * 100) if total > 0 else 0
        
        result = f"""【{self.doc_name}签订统计】（{msg_type}）
━━━━━━━━━━━━━━━━━━━━
总用户数：{total}
已同意：{agreed}
已拒绝：{refused}
等待中：{waiting}
同意率：{rate:.1f}%"""
        
        yield event.plain_result(result)
        event.stop_event()

    @register.command("doc_list")
    async def cmd_list(self, event: AstrMessageEvent):
        """查看用户列表（仅管理员）"""
        if not self._is_admin(event.get_sender_id()):
            yield event.plain_result("只有管理员可以使用此命令。")
            event.stop_event()
            return
        
        stat_key = self._get_stat_key(event)
        msg_type = "私聊" if event.get_message_type() == "private" else "本群"
        user_list = await self.get_kv_data(f"{stat_key}_users", [])
        
        agreed, refused, waiting = [], [], []
        for uid in user_list:
            if event.get_message_type() == "private":
                session = f"doc_agree_{uid}"
            else:
                session = f"doc_agree_{event.get_group_id()}_{uid}"
            status = await self.get_kv_data(session, None)
            
            if status == self.STATE_AGREED:
                agreed.append(uid)
            elif status == self.STATE_REFUSED:
                refused.append(uid)
            elif status == self.STATE_WAITING:
                waiting.append(uid)
        
        max_display = 30
        result = f"【{self.doc_name}用户列表】（{msg_type}）\n\n"
        result += f"✅ 已同意 ({len(agreed)}人)：\n"
        result += "、".join(agreed[:max_display]) if agreed else "无"
        result += f"\n\n❌ 已拒绝 ({len(refused)}人)：\n"
        result += "、".join(refused[:max_display]) if refused else "无"
        result += f"\n\n⏳ 等待中 ({len(waiting)}人)：\n"
        result += "、".join(waiting[:max_display]) if waiting else "无"
        
        yield event.plain_result(result)
        event.stop_event()

    @register.command("doc_reset")
    async def cmd_reset(self, event: AstrMessageEvent):
        """重置统计数据（仅管理员）"""
        if not self._is_admin(event.get_sender_id()):
            yield event.plain_result("只有管理员可以使用此命令。")
            event.stop_event()
            return
        
        stat_key = self._get_stat_key(event)
        msg_type = "私聊" if event.get_message_type() == "private" else "本群"
        
        await self.put_kv_data(f"{stat_key}_total", 0)
        await self.put_kv_data(f"{stat_key}_agreed", 0)
        await self.put_kv_data(f"{stat_key}_refused", 0)
        await self.put_kv_data(f"{stat_key}_users", [])
        
        yield event.plain_result(f"已重置{msg_type}的统计数据。")
        event.stop_event()

    @register.command("doc_reload")
    async def cmd_reload(self, event: AstrMessageEvent):
        """重新加载配置（仅管理员）"""
        if not self._is_admin(event.get_sender_id()):
            yield event.plain_result("只有管理员可以使用此命令。")
            event.stop_event()
            return
        
        self._load_config()
        
        delivery_modes = []
        if self.delivery_text:
            delivery_modes.append("文字")
        if self.delivery_image:
            delivery_modes.append("图片")
        
        yield event.plain_result(
            f"配置已重新加载。\n"
            f"文档名称：{self.doc_name}\n"
            f"发送方式：{'+'.join(delivery_modes) if delivery_modes else '无'}\n"
            f"触发词：{', '.join(self.trigger_keywords)}\n"
            f"私聊：{'启用' if self.scope_private else '禁用'}\n"
            f"群聊：{'启用' if self.scope_group else '禁用'}"
        )
        event.stop_event()

    @register.command("doc_status")
    async def cmd_status(self, event: AstrMessageEvent):
        """查看个人文档签订状态"""
        session = self._get_session_key(event)
        status = await self.get_kv_data(session, None)
        
        status_map = {
            None: "未签订",
            self.STATE_WAITING: "待确认",
            self.STATE_AGREED: "已同意",
            self.STATE_REFUSED: "已拒绝"
        }
        
        result = f"【{self.doc_name}状态】\n当前状态：{status_map.get(status, '未知')}"
        
        if status == self.STATE_AGREED:
            agree_time = await self.get_kv_data(f"{session}_time", None)
            if agree_time:
                result += f"\n同意时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(agree_time))}"
        
        yield event.plain_result(result)
        event.stop_event()

    @register.command("doc_help")
    async def cmd_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        delivery_modes = []
        if self.delivery_text:
            delivery_modes.append("文字")
        if self.delivery_image:
            delivery_modes.append("图片")
        
        help_text = f"""【{self.doc_name}插件帮助】

触发方式：
发送包含「{'」、「'.join(self.trigger_keywords)}」的消息

发送方式：{' + '.join(delivery_modes) if delivery_modes else '未启用'}

当前状态：
私聊：{'✅ 启用' if self.scope_private else '❌ 禁用'}
群聊：{'✅ 启用' if self.scope_group else '❌ 禁用'}

📊 用户命令：
/doc_stats  - 查看统计
/doc_status - 查看个人状态
/doc_help   - 显示本帮助

🔧 管理员命令：
/doc_list   - 查看用户列表
/doc_reset  - 重置统计
/doc_reload - 重载配置

💡 提示：
回复「同意」接受文档，回复「不同意」拒绝
图片协议需配置图片URL或本地路径
配置可在 WebUI → 插件配置 中修改

版本：{self.doc_version}
更新：{self.doc_updated}"""
        
        yield event.plain_result(help_text)
        event.stop_event()

    async def terminate(self):
        """插件终止时调用"""
        logger.info("文档签订插件已终止")