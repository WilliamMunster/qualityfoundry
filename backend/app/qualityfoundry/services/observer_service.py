"""QualityFoundry - Observer Service

上帝视角服务 - 提供全链路监督、一致性检查和改进建议
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from qualityfoundry.database.models import Requirement, Scenario, TestCase, Execution
from qualityfoundry.database.ai_config_models import AIStep
from qualityfoundry.services.ai_service import AIService

logger = logging.getLogger(__name__)

class ObserverError(Exception):
    """上帝视角服务异常"""
    pass

def estimate_tokens(text: str) -> int:
    """
    极简的 Token 估算 (基于字符数/4)
    实际生产环境建议使用 tiktoken 或 similar library
    """
    return len(text) // 4

def truncate_context(context: str, max_tokens: int = 6000) -> str:
    """
    根据 Token 限制截断上下文
    """
    if estimate_tokens(context) <= max_tokens:
        return context
    
    # 简单的截断逻辑
    logger.warning(f"Context too long, truncating to ~{max_tokens} tokens")
    return context[:max_tokens * 4] + "... [Context Truncated]"

class ObserverService:
    """上帝视角服务"""

    @staticmethod
    async def analyze_consistency(
        db: Session,
        requirement_id: UUID,
        config_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析需求与生成产物（场景、用例）的一致性
        """
        req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
        if not req:
            raise ObserverError("Requirement not found")

        # 获取关联的场景和用例
        scenarios = req.scenarios
        all_cases = []
        for s in scenarios:
            all_cases.extend(s.testcases)

        # 构建分析提示词变量
        context = {
            "requirement": req.content or req.title,
            "scenarios": [
                {
                    "title": s.title,
                    "description": s.description,
                    "steps": s.steps
                } for s in scenarios
            ],
            "testcases": [
                {
                    "title": tc.title,
                    "steps": tc.steps,
                    "expected": tc.expected_results
                } for tc in all_cases
            ]
        }

        # 调用 AI 进行全链路分析
        try:
            analysis_result = await AIService.call_ai(
                db=db,
                step=AIStep.GLOBAL_OBSERVER,
                prompt_variables={"context": truncate_context(str(context))},
                config_id=config_id
            )
            return {
                "requirement_id": requirement_id,
                "analysis": analysis_result,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Observer analysis failed: {e}")
            raise ObserverError(f"Consistency analysis failed: {str(e)}")

    @staticmethod
    async def evaluate_coverage(
        db: Session,
        requirement_id: UUID,
        config_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        评估测试覆盖度
        """
        req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
        if not req:
            raise ObserverError("Requirement not found")

        scenarios = req.scenarios
        context = {
            "requirement": req.content or req.title,
            "scenarios": [
                {
                    "title": s.title,
                    "description": s.description
                } for s in scenarios
            ]
        }

        try:
            coverage_result = await AIService.call_ai(
                db=db,
                step=AIStep.GLOBAL_OBSERVER,
                prompt_variables={"context": truncate_context(str(context))},
                system_prompt="你是一位资深的质量保障专家，请分析以下需求和测试场景的覆盖度，并指出缺失的测试点。",
                config_id=config_id
            )
            return {
                "requirement_id": requirement_id,
                "coverage_analysis": coverage_result,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Coverage evaluation failed: {e}")
            raise ObserverError(f"Coverage evaluation failed: {str(e)}")

    @staticmethod
    async def get_god_suggestions(
        db: Session,
        requirement_id: UUID,
        config_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成“上帝建议”
        """
        req = db.query(Requirement).filter(Requirement.id == requirement_id).first()
        if not req:
            raise ObserverError("Requirement not found")

        # 聚合所有产物进行深度建议生成
        context = {
            "requirement": req.content or req.title,
            "scenarios_count": len(req.scenarios)
        }

        try:
            suggestions = await AIService.call_ai(
                db=db,
                step=AIStep.GLOBAL_OBSERVER,
                prompt_variables={"context": truncate_context(str(context))},
                system_prompt="你拥有上帝视角，请根据当前需求和测试现状，给出针对性的研发与测试改进建议。",
                config_id=config_id
            )
            return {
                "requirement_id": requirement_id,
                "suggestions": suggestions,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"God suggestions failed: {e}")
            raise ObserverError(f"God suggestions failed: {str(e)}")

    @staticmethod
    async def analyze_execution_failure(
        db: Session,
        execution_id: UUID,
        config_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析执行失败原因
        """
        execution = db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            raise ObserverError("Execution not found")

        # 获取上下文：用例、执行结果、错误信息
        testcase = execution.testcase
        context = {
            "testcase_title": testcase.title,
            "steps": testcase.steps,
            "status": execution.status,
            "error_message": execution.error_message,
            "evidence_count": len(execution.evidence or [])
        }

        try:
            analysis = await AIService.call_ai(
                db=db,
                step=AIStep.EXECUTION_ANALYSIS,
                prompt_variables={"execution_data": truncate_context(str(context))},
                config_id=config_id
            )
            
            # 使用 flush 而非 commit，将事务管理权提交给外层
            if execution.result is None:
                execution.result = {}
            
            execution.result["ai_analysis"] = analysis
            db.flush() 
            
            return {
                "execution_id": execution_id,
                "ai_analysis": analysis,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Execution failure analysis failed: {e}")
            raise ObserverError(f"Execution analysis failed: {str(e)}")
