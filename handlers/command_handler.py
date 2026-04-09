"""命令处理"""

import time
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger

# 修改这里：使用 .. 表示上一级目录
from ..core import (
    PluginConfig, AgreementState, AgreementStorage,
    is_admin, extract_user_id, extract_group_id, is_private_chat
)


class CommandHandler:
    """命令处理器"""

    def __init__(self, config: PluginConfig, storage: AgreementStorage):
        self.config = config
        self.storage = storage

    async def _is_rejected(self, user_id: str, group_id: str = None) -> bool:
        """检查用户是否处于拒绝状态（管理员不受限）"""
        if is_admin(user_id, self.config.admins):
            return False
        status = await self.storage.get_state(user_id, group_id)
        return status == AgreementState.REFUSED

    # ==================== 用户命令 ====================

    async def cmd_stats(self, event: AstrMessageEvent):
        """查看统计（拒绝用户不可用）"""
        user_id = extract_user_id(event)
        group_id = extract_group_id(event)

        if await self._is_rejected(user_id, group_id):
            event.stop_event()
            return

        stats = await self.storage.get_stat(group_id)
        msg_type = "私聊" if is_private_chat(event) else "本群"
        waiting = stats["total"] - stats["agreed"] - stats["refused"]
        rate = (stats["agreed"] / stats["total"] * 100) if stats["total"] > 0 else 0

        result = f"【{self.config.doc_name}签订统计】（{msg_type}）\n━━━━━━━━━━━━━━━━━━━━\n总用户数：{stats['total']}\n已同意：{stats['agreed']}\n已拒绝：{stats['refused']}\n等待中：{waiting}\n同意率：{rate:.1f}%"
        yield event.plain_result(result)
        event.stop_event()

    async def cmd_status(self, event: AstrMessageEvent):
        """查看个人状态（拒绝用户也可用）"""
        user_id = extract_user_id(event)
        group_id = extract_group_id(event)

        status = await self.storage.get_state(user_id, group_id)

        status_map = {
            None: "未签订",
            AgreementState.WAITING: "待确认",
            AgreementState.AGREED: "已同意",
            AgreementState.REFUSED: "已拒绝 ❌ （机器人将不回复你的消息）"
        }

        result = f"【{self.config.doc_name}状态】\n当前状态：{status_map.get(status, '未知')}"

        if status == AgreementState.AGREED:
            agree_time = await self.storage.get_user_data(user_id, "time", 0, group_id)
            if agree_time:
                result += f"\n同意时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(agree_time))}"

        yield event.plain_result(result)
        event.stop_event()

    async def cmd_undo(self, event: AstrMessageEvent):
        """反悔：重新签订协议（拒绝用户也可用）"""
        user_id = extract_user_id(event)
        group_id = extract_group_id(event)

        if not self.config.allow_undo:
            yield event.plain_result("❌ 反悔功能已禁用，请联系管理员。")
            event.stop_event()
            return

        status = await self.storage.get_state(user_id, group_id)

        if status not in [AgreementState.AGREED, AgreementState.REFUSED]:
            yield event.plain_result("你还没有签订过协议，无需反悔。")
            event.stop_event()
            return

        undo_count = await self.storage.get_user_data(user_id, "undo_count", 0, group_id)
        if undo_count >= self.config.max_undo:
            yield event.plain_result(f"❌ 你已达到最大反悔次数（{self.config.max_undo}次），请联系管理员。")
            event.stop_event()
            return

        last_undo = await self.storage.get_user_data(user_id, "last_undo", 0, group_id)
        if time.time() - last_undo < self.config.undo_cooldown:
            remaining_hours = int((self.config.undo_cooldown - (time.time() - last_undo)) / 3600)
            yield event.plain_result(f"⏰ 反悔冷却中，请等待 {remaining_hours} 小时后再试。")
            event.stop_event()
            return

        await self.storage.set_state(user_id, None, group_id)
        await self.storage.set_user_data(user_id, "undo_count", undo_count + 1, group_id)
        await self.storage.set_user_data(user_id, "last_undo", time.time(), group_id)

        remaining = self.config.max_undo - undo_count - 1
        yield event.plain_result(f"✅ 已清除你的协议状态。\n可重新发送「{self.config.trigger_keywords[0]}」开始签订。\n剩余反悔次数：{remaining}")
        event.stop_event()

    async def cmd_help(self, event: AstrMessageEvent):
        """显示帮助（拒绝用户不可用）"""
        user_id = extract_user_id(event)
        group_id = extract_group_id(event)

        if await self._is_rejected(user_id, group_id):
            event.stop_event()
            return

        delivery_modes = ["文字"] if self.config.delivery_text else []
        agree_example = "、".join(self.config.agree_keywords[:3])
        refuse_example = "、".join(self.config.refuse_keywords[:3])

        help_text = f"""【{self.config.doc_name}插件帮助】

触发方式：
私聊：发送任意消息
群聊：@机器人 并发送任意消息

发送方式：{' + '.join(delivery_modes) if delivery_modes else '未启用'}

当前状态：
私聊：{'✅ 启用' if self.config.scope_private else '❌ 禁用'}
群聊：{'✅ 启用' if self.config.scope_group else '❌ 禁用'}

📝 协议签订：
发送触发词（如「{self.config.trigger_keywords[0]}」）获取协议
回复「{agree_example}」表示同意
回复「{refuse_example}」表示拒绝

📊 用户命令：
/doc_stats  - 查看统计
/doc_status - 查看个人状态
/doc_undo   - 反悔，重新签订协议
/doc_help   - 显示本帮助

🔧 管理员命令：
/doc_list   - 查看用户列表
/doc_reset  - 重置统计
/doc_reset_user 用户QQ号 - 重置指定用户状态
/doc_reload - 重载配置

💡 提示：
如果被拒绝，机器人将完全静默，可使用 /doc_status 查看状态，使用 /doc_undo 反悔
管理员不受拒绝状态限制，可正常使用所有命令
配置可在 WebUI → 插件配置 中修改

版本：{self.config.doc_version}
更新：{self.config.doc_updated}"""

        yield event.plain_result(help_text)
        event.stop_event()

    # ==================== 管理员命令 ====================

    async def cmd_list(self, event: AstrMessageEvent):
        """查看用户列表"""
        user_id = extract_user_id(event)
        group_id = extract_group_id(event)

        if await self._is_rejected(user_id, group_id):
            event.stop_event()
            return

        if not is_admin(user_id, self.config.admins):
            yield event.plain_result("只有管理员可以使用此命令。")
            event.stop_event()
            return

        stats = await self.storage.get_stat(group_id)
        msg_type = "私聊" if is_private_chat(event) else "本群"

        agreed, refused, waiting = [], [], []
        for uid in stats["users"]:
            status = await self.storage.get_state(uid, group_id)
            if status == AgreementState.AGREED:
                agreed.append(uid)
            elif status == AgreementState.REFUSED:
                refused.append(uid)
            elif status == AgreementState.WAITING:
                waiting.append(uid)

        max_display = 30
        result = f"【{self.config.doc_name}用户列表】（{msg_type}）\n\n✅ 已同意 ({len(agreed)}人)：\n"
        result += "、".join(agreed[:max_display]) if agreed else "无"
        result += f"\n\n❌ 已拒绝 ({len(refused)}人)：\n"
        result += "、".join(refused[:max_display]) if refused else "无"
        result += f"\n\n⏳ 等待中 ({len(waiting)}人)：\n"
        result += "、".join(waiting[:max_display]) if waiting else "无"

        yield event.plain_result(result)
        event.stop_event()

    async def cmd_reset(self, event: AstrMessageEvent):
        """重置统计数据"""
        user_id = extract_user_id(event)
        group_id = extract_group_id(event)

        if await self._is_rejected(user_id, group_id):
            event.stop_event()
            return

        if not is_admin(user_id, self.config.admins):
            yield event.plain_result("只有管理员可以使用此命令。")
            event.stop_event()
            return

        await self.storage.reset_stat(group_id)
        msg_type = "私聊" if is_private_chat(event) else "本群"
        yield event.plain_result(f"已重置{msg_type}的统计数据。")
        event.stop_event()

    async def cmd_reset_user(self, event: AstrMessageEvent, target_user_id: str = ""):
        """重置指定用户状态"""
        user_id = extract_user_id(event)
        group_id = extract_group_id(event)

        if await self._is_rejected(user_id, group_id):
            event.stop_event()
            return

        if not is_admin(user_id, self.config.admins):
            yield event.plain_result("只有管理员可以使用此命令。")
            event.stop_event()
            return

        if not target_user_id:
            yield event.plain_result("用法：/doc_reset_user 用户QQ号")
            event.stop_event()
            return

        await self.storage.set_state(target_user_id, None, group_id)
        yield event.plain_result(f"✅ 已重置用户 {target_user_id} 的协议状态。")
        event.stop_event()

    async def cmd_reload(self, event: AstrMessageEvent):
        """热重载配置"""
        user_id = extract_user_id(event)

        if not is_admin(user_id, self.config.admins):
            yield event.plain_result("只有管理员可以使用此命令。")
            event.stop_event()
            return

        yield event.plain_result("配置重载功能需要在 main.py 中实现。")
        event.stop_event()
