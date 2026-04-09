async def handle(self, event: AstrMessageEvent):
    """处理普通消息，使用 yield 返回结果"""
    
    # === 防御性检查 ===
    if not hasattr(self, 'config') or self.config is None:
        logger.error("配置未初始化")
        return
    
    # 如果 config 是字符串，说明出问题了
    if isinstance(self.config, str):
        logger.error(f"config 是字符串类型: {self.config}")
        return
    
    # 确保 delivery_text 存在
    if not hasattr(self.config, 'delivery_text') or not self.config.delivery_text:
        return
    
    # ... 原有代码继续
