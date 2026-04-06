from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.event import EventMessageType
from astrbot.api.message_components import Image, Plain
from astrbot.api import logger, AstrBotConfig
import time
import os
import httpx
import asyncio


@register(
    "astrbot_plugin_agreement",
    "星恒梦落",
    "文档签订插件，首次触发关键词时发送文档（文字/图片），记录用户同意/拒绝状态",
    "1.0.0"
)
class AgreementPlugin(Star):
    """文档签订插件主类"""

    STATE_NONE = None
    STATE_WAITING = "waiting"
    STATE_AGREED = "yes"
    STATE_REFUSED = "no"

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self._load_config()
        self._log_config()

    def _load_config(self) -> None:
        """加载所有配置"""
        cfg = self.config
        
        self.admins = cfg.get("admins", [])
        self.scope_private = cfg.get("scope_private", True)
        self.scope_group = cfg.get("scope_group", False)
        self.doc_name = cfg.get("doc_name", "用户协议")
        self.doc_version = cfg.get("doc_version", "v1.0")
        self.doc_updated = cfg.get("doc_updated", "2026-04-06")
        self.doc_contact = cfg.get("doc_contact", "QQ群 752775661")
        self.trigger_keywords = cfg.get("trigger_keywords", ["协议", "规则", "条例"])
        self.cooldown_seconds = cfg.get("cooldown_seconds", 30)
        self.delivery_text = cfg.get("delivery_text", True)
        self.delivery_image = cfg.get("delivery_image", False)
        self.image_url = cfg.get("image_url", "")
        self.image_path = cfg.get("image_path", "")
        self.reply_agree = cfg.get("reply_agree", "已记录你的同意。现在可以正常使用本机器人。")
        self.reply_refuse = cfg.get("reply_refuse", "已记录你的拒绝。本机器人将无法为你服务。")
        self.reply_waiting = cfg.get("reply_waiting", "请回复「同意」或「不同意」接受{name}。")
        self.sections = cfg.get("doc_sections", [])
        
        self.doc_text = self._build_document() if self.delivery_text else ""

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

    # ==================== 工具方法 ====================

    def _format_reply(self, template: str) -> str:
        """格式化回复内容"""
        return template.replace("{name}", self.doc_name)

    def _is_admin(self, uid: str) -> bool:
        """检查是否为管理员"""
        return uid in self.admins

    def _contains_keyword(self, text: str) -> bool:
        """检查文本是否包含触发关键词"""
        return any(kw in text for kw in self.trigger_keywords)

    def _get_session_key(self, event: AstrMessageEvent) -> str:
        """获取会话存储键"""
        if event.get_message_type() == "private":
            return f"doc_agree_{event.get_sender_id()}"
        return f"doc_agree_{event.get_group_id()}_{event.get_sender_id()}"

    def _get_stat_key(self, event: AstrMessageEvent) -> str:
        """获取统计存储键"""
        if event.get_message_type() == "private":
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

    # ==================== 图片发送 ====================

    async def _send_image(self, event: AstrMessageEvent):
        """发送图片协议"""
        image_data = None
        
        if self.image_url and self.image_url.strip():
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(self.image_url)
                    if response.status_code == 200:
                        image_data = response.content
            except Exception as e:
                logger.error(f"加载网络图片失败: {e}")
        
        if image_data is None and self.image_path and os.path.exists(self.image_path):
            try:
                with open(self.image_path, "rb") as f:
                    image_data = f.read()
            except Exception as e:
                logger.error(f"加载本地图片失败: {e}")
        
        if image_data:
            yield event.reply([Image.from_bytes(image_data)])
        elif self.delivery_text:
            yield event.plain_result(self.doc_text)

    async def _send_document(self, event: AstrMessageEvent):
        """发送文档"""
        if self.delivery_image:
            async for r in self._send_image(event):
                yield r
        elif self.delivery_text:
            yield event.plain_result(self.doc_text)

    # ==================== 统计方法 ====================

    async def _update_stat(self, stat_key: str, field: str, delta: int = 1) -> None:
        key = f"{stat_key}_{field}"
        current = await self.get_kv_data(key, 0)
        await self.put_kv_data(key, current + delta)

    async def _get_stat(self, stat_key: str, field: str) -> int:
        return await self.get_kv_data(f"{stat_key}_{field}", 0)

    async def _add_to_user_list(self, stat_key: str, uid: str) -> None:
        user_list = await self.get_kv_data(f"{stat_key}_users", [])
        if uid not in user_list:
            user_list.append(uid)
            await self.put_kv_data(f"{stat_key}_users", user_list)
            await self._update_stat(stat_key, "total")

    # ==================== 消息处理 ====================

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        """监听所有消息，实现状态机"""
        if not self._should_process(event):
            return
        
        if not self.delivery_text and not self.delivery_image:
            return
        
        session = self._get_session_key(event)
        stat_key = self._get_stat_key(event)
        status = await self.get_kv_data(session, None)
        
        try:
            # 状态1：未签订（None）- 任何消息都触发
            if status is None:
                logger.info(f"用户 {event.get_sender_id()} 未签订，发送协议")
                await self.put_kv_data(session, self.STATE_WAITING)
                await self.put_kv_data(f"{session}_last", time.time())
                await self._add_to_user_list(stat_key, event.get_sender_id())
                async for r in self._send_document(event):
                    yield r
                event.stop_event()
                return
            
            # 状态2：等待确认（waiting）
            if status == self.STATE_WAITING:
                msg = event.message_str
                if "同意" in msg:
                    logger.info(f"用户 {event.get_sender_id()} 同意文档")
                    await self.put_kv_data(session, self.STATE_AGREED)
                    await self.put_kv_data(f"{session}_time", time.time())
                    await self._update_stat(stat_key, "agreed")
                    yield event.plain_result(self._format_reply(self.reply_agree))
                    event.stop_event()
                elif "不同意" in msg:
                    logger.info(f"用户 {event.get_sender_id()} 拒绝文档")
                    await self.put_kv_data(session, self.STATE_REFUSED)
                    await self.put_kv_data(f"{session}_time", time.time())
                    await self._update_stat(stat_key, "refused")
                    yield event.plain_result(self._format_reply(self.reply_refuse))
                    event.stop_event()
                else:
                    # 其他消息，重新发送协议
                    logger.info(f"用户 {event.get_sender_id()} 状态为waiting，重新发送协议")
                    async for r in self._send_document(event):
                        yield r
                    event.stop_event()
                return
            
            # 状态3：已拒绝（no）
            if status == self.STATE_REFUSED:
                event.stop_event()
                return
            
            # 状态4：已同意（yes），放行
            return
            
        except Exception as e:
            logger.error(f"文档插件处理消息时出错: {e}")
            yield event.plain_result("处理消息时出现错误，请稍后再试。")
            event.stop_event()

    # ==================== 管理员命令 ====================

    @filter.command("doc_stats")
    async def cmd_stats(self, event: AstrMessageEvent):
        """查看文档签订统计"""
        stat_key = self._get_stat_key(event)
        msg_type = "私聊" if event.get_message_type() == "private" else "本群"
        
        total = await self._get_stat(stat_key, "total")
        agreed = await self._get_stat(stat_key, "agreed")
        refused = await self._get_stat(stat_key, "refused")
        waiting = total - agreed - refused
        rate = (agreed / total * 100) if total > 0 else 0
        
        result = f"【{self.doc_name}签订统计】（{msg_type}）\n━━━━━━━━━━━━━━━━━━━━\n总用户数：{total}\n已同意：{agreed}\n已拒绝：{refused}\n等待中：{waiting}\n同意率：{rate:.1f}%"
        yield event.plain_result(result)
        event.stop_event()

    @filter.command("doc_list")
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
        result = f"【{self.doc_name}用户列表】（{msg_type}）\n\n✅ 已同意 ({len(agreed)}人)：\n"
        result += "、".join(agreed[:max_display]) if agreed else "无"
        result += f"\n\n❌ 已拒绝 ({len(refused)}人)：\n"
        result += "、".join(refused[:max_display]) if refused else "无"
        result += f"\n\n⏳ 等待中 ({len(waiting)}人)：\n"
        result += "、".join(waiting[:max_display]) if waiting else "无"
        
        yield event.plain_result(result)
        event.stop_event()

    @filter.command("doc_reset")
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

    @filter.command("doc_reload")
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

    @filter.command("doc_status")
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

    @filter.command("doc_help")
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
        logger.info("文档签订插件已终止")
