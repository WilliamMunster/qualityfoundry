"""QualityFoundry - AI Service

AI 服务 - 支持多模型配置
"""
from typing import Optional, Dict, Any
import httpx
from sqlalchemy.orm import Session

from qualityfoundry.database.ai_config_models import AIConfig, AIStep


class AIService:
    """AI 服务"""
    
    @staticmethod
    async def call_ai(
        db: Session,
        step: AIStep,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        调用 AI 模型
        
        Args:
            db: 数据库会话
            step: 执行步骤
            prompt: 用户提示词
            system_prompt: 系统提示词
        
        Returns:
            AI 响应内容
        """
        # 查找该步骤绑定的配置
        config = AIService.get_config_for_step(db, step)
        
        if not config:
            # 使用默认配置
            config = db.query(AIConfig).filter(
                AIConfig.is_default == True,
                AIConfig.is_active == True
            ).first()
        
        if not config:
            raise ValueError("未找到可用的 AI 配置")
        
        # 调用 AI API
        return await AIService.call_openai_compatible(
            config=config,
            prompt=prompt,
            system_prompt=system_prompt
        )
    
    @staticmethod
    def get_config_for_step(db: Session, step: AIStep) -> Optional[AIConfig]:
        """获取步骤绑定的配置"""
        configs = db.query(AIConfig).filter(
            AIConfig.is_active == True
        ).all()
        
        for config in configs:
            if config.assigned_steps and step.value in config.assigned_steps:
                return config
        
        return None
    
    @staticmethod
    async def call_openai_compatible(
        config: AIConfig,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        调用 OpenAI 兼容接口
        
        支持 OpenAI、DeepSeek、Anthropic 等兼容接口
        """
        # 构建请求 URL
        base_url = config.base_url or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"
        
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 构建请求体
        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": float(config.temperature),
            "max_tokens": int(config.max_tokens),
            "top_p": float(config.top_p),
        }
        
        # 添加额外参数
        if config.extra_params:
            payload.update(config.extra_params)
        
        # 发送请求
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 提取响应内容
            return result["choices"][0]["message"]["content"]
    
    @staticmethod
    async def test_config(config: AIConfig, prompt: str = "Hello") -> Dict[str, Any]:
        """测试 AI 配置"""
        try:
            response = await AIService.call_openai_compatible(
                config=config,
                prompt=prompt
            )
            return {
                "success": True,
                "response": response,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "response": None,
                "error": str(e)
            }
