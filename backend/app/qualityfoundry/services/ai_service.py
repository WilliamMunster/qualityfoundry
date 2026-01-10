"""QualityFoundry - AI Service

AI 服务 - 支持多模型配置、重试机制、响应验证
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from qualityfoundry.database.ai_config_models import AIConfig, AIStep

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """生成配置"""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.95
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 60.0


class AIServiceError(Exception):
    """AI 服务错误"""
    pass


class AIService:
    """AI 服务"""
    
    @staticmethod
    async def call_ai(
        db: Session,
        step: AIStep,
        prompt: str,
        system_prompt: Optional[str] = None,
        generation_config: Optional[GenerationConfig] = None
    ) -> str:
        """
        调用 AI 模型（带重试机制）
        
        Args:
            db: 数据库会话
            step: 执行步骤
            prompt: 用户提示词
            system_prompt: 系统提示词
            generation_config: 生成配置
        
        Returns:
            AI 响应内容
        """
        config = AIService.get_config_for_step(db, step)
        
        if not config:
            config = db.query(AIConfig).filter(
                AIConfig.is_default,
                AIConfig.is_active
            ).first()
        
        if not config:
            raise AIServiceError("未找到可用的 AI 配置")
        
        gen_config = generation_config or GenerationConfig()
        
        # 如果配置中有温度和 max_tokens 设置，使用配置值
        gen_config.temperature = float(config.temperature)
        gen_config.max_tokens = int(config.max_tokens)
        gen_config.top_p = float(config.top_p)
        
        return await AIService.call_with_retry(
            config=config,
            prompt=prompt,
            system_prompt=system_prompt,
            gen_config=gen_config
        )
    
    @staticmethod
    def get_config_for_step(db: Session, step: AIStep) -> Optional[AIConfig]:
        """获取步骤绑定的配置"""
        configs = db.query(AIConfig).filter(
            AIConfig.is_active
        ).all()
        
        for config in configs:
            if config.assigned_steps and step.value in config.assigned_steps:
                return config
        
        return None
    
    @staticmethod
    async def call_with_retry(
        config: AIConfig,
        prompt: str,
        system_prompt: Optional[str] = None,
        gen_config: Optional[GenerationConfig] = None,
        validator: Optional[Callable[[str], bool]] = None
    ) -> str:
        """
        带重试机制的 AI 调用
        
        Args:
            config: AI 配置
            prompt: 用户提示词
            system_prompt: 系统提示词
            gen_config: 生成配置
            validator: 响应验证函数
        
        Returns:
            AI 响应内容
        
        Raises:
            AIServiceError: 重试次数用尽或验证失败
        """
        gen_config = gen_config or GenerationConfig()
        last_error = None
        
        for attempt in range(gen_config.max_retries):
            try:
                response = await AIService.call_openai_compatible(
                    config=config,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    gen_config=gen_config
                )
                
                # 验证响应（如果提供了验证器）
                if validator and not validator(response):
                    logger.warning(f"AI 响应验证失败 (尝试 {attempt + 1}/{gen_config.max_retries})")
                    last_error = AIServiceError("响应验证失败")
                    continue
                
                return response
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"AI API 错误 (尝试 {attempt + 1}/{gen_config.max_retries}): {e}")
                last_error = e
                if e.response.status_code == 429:  # Rate limit
                    import asyncio
                    await asyncio.sleep(gen_config.retry_delay * (attempt + 1))
                continue
                
            except httpx.TimeoutException as e:
                logger.warning(f"AI API 超时 (尝试 {attempt + 1}/{gen_config.max_retries})")
                last_error = e
                continue
                
            except Exception as e:
                logger.error(f"AI 调用未知错误: {e}")
                last_error = e
                break
        
        raise AIServiceError(f"AI 调用失败 (已重试 {gen_config.max_retries} 次): {last_error}")
    
    @staticmethod
    async def call_openai_compatible(
        config: AIConfig,
        prompt: str,
        system_prompt: Optional[str] = None,
        gen_config: Optional[GenerationConfig] = None
    ) -> str:
        """
        调用 OpenAI 兼容接口
        
        支持 OpenAI、DeepSeek、Anthropic 等兼容接口
        """
        gen_config = gen_config or GenerationConfig()
        
        base_url = config.base_url or "https://api.openai.com/v1"
        url = f"{base_url}/chat/completions"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": gen_config.temperature,
            "max_tokens": gen_config.max_tokens,
            "top_p": gen_config.top_p,
        }
        
        if config.extra_params:
            payload.update(config.extra_params)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=gen_config.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
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


# ================== 生成验证器 ==================

def validate_scenario_response(response: str) -> bool:
    """验证场景生成响应"""
    # 检查必须包含的关键字
    required_keywords = ["步骤", "场景", "测试"]
    has_keywords = any(kw in response for kw in required_keywords)
    
    # 检查最小长度
    min_length = 50
    
    return has_keywords and len(response) >= min_length


def validate_testcase_response(response: str) -> bool:
    """验证用例生成响应"""
    required_keywords = ["用例", "步骤", "预期"]
    has_keywords = any(kw in response for kw in required_keywords)
    
    min_length = 100
    
    return has_keywords and len(response) >= min_length


def validate_json_response(response: str) -> bool:
    """验证 JSON 响应"""
    import json
    try:
        json.loads(response)
        return True
    except json.JSONDecodeError:
        return False


# ================== 提示词模板 ==================

SCENARIO_GENERATION_PROMPT = """你是一个专业的测试场景分析师。

## 任务
根据以下需求，生成测试场景。

## 需求内容
{requirement}

## 要求
1. 生成 3-5 个测试场景
2. 每个场景包含：标题、描述、测试步骤
3. 考虑正向场景和异常场景
4. 步骤要具体可执行

## 输出格式
请按以下 JSON 格式输出：
```json
[
  {{
    "title": "场景标题",
    "description": "场景描述",
    "steps": ["步骤1", "步骤2", "步骤3"]
  }}
]
```
"""

TESTCASE_GENERATION_PROMPT = """你是一个专业的测试用例设计师。

## 任务
根据以下测试场景，生成详细的测试用例。

## 场景内容
{scenario}

## 要求
1. 每个场景生成 2-3 个测试用例
2. 每个用例包含：标题、前置条件、测试步骤、预期结果
3. 步骤要详细具体
4. 包含测试数据示例

## 输出格式
请按以下 JSON 格式输出：
```json
[
  {{
    "title": "用例标题",
    "preconditions": ["前置条件1", "前置条件2"],
    "steps": [
      {{"step": "操作步骤", "expected": "预期结果"}}
    ],
    "priority": "P0/P1/P2",
    "tags": ["tag1", "tag2"]
  }}
]
```
"""
