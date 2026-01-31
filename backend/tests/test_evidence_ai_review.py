"""Test Evidence with AI Review Integration

Evidence 与 AI 评审集成测试
"""
import json
from uuid import uuid4
from pathlib import Path
import tempfile

from qualityfoundry.governance.tracing.collector import (
    TraceCollector,
    Evidence,
    ToolCallSummary,
)
from qualityfoundry.governance.ai_review import (
    AIReviewConfig,
    AIReviewEngine,
    AIReviewResult,
    AIMetadata,
    ModelConfig,
    StrategyType,
    VerdictType,
)


class TestEvidenceWithAIReview:
    """测试 Evidence 包含 AI 评审结果"""

    def test_evidence_has_ai_review_field(self):
        """Evidence 模型有 ai_review 字段"""
        evidence = Evidence(
            run_id=str(uuid4()),
            input_nl="Test",
            ai_review={
                "verdict": "PASS",
                "confidence": 0.92,
                "model_votes": [],
            },
        )
        
        assert evidence.ai_review is not None
        assert evidence.ai_review["verdict"] == "PASS"
        assert evidence.ai_review["confidence"] == 0.92

    def test_evidence_ai_review_none_by_default(self):
        """默认 ai_review 为 None"""
        evidence = Evidence(
            run_id=str(uuid4()),
            input_nl="Test",
        )
        
        assert evidence.ai_review is None

    def test_evidence_extra_allow_schema(self):
        """Evidence 允许额外字段（用于 ai_review）"""
        evidence = Evidence(
            run_id=str(uuid4()),
            input_nl="Test",
            ai_review={
                "verdict": "PASS",
                "confidence": 0.95,
                "model_votes": [
                    {"model": "gpt-4", "verdict": "PASS", "confidence": 0.96},
                ],
                "metadata": {"review_id": "test-123"},
            },
        )
        
        # 验证可以序列化
        json_str = evidence.model_dump_json_for_file()
        data = json.loads(json_str)
        
        assert "ai_review" in data
        assert data["ai_review"]["verdict"] == "PASS"
        assert data["ai_review"]["confidence"] == 0.95


class TestTraceCollectorAIReview:
    """测试 TraceCollector 设置 AI 评审结果"""

    def test_collector_set_ai_review_result(self):
        """Collector 可以设置 AI 评审结果"""
        collector = TraceCollector(
            run_id=str(uuid4()),
            input_nl="Test scenario",
        )
        
        ai_result = {
            "verdict": "PASS",
            "confidence": 0.88,
            "reasoning": "All checks passed",
            "model_votes": [
                {"model": "gpt-4", "verdict": "PASS", "confidence": 0.9},
            ],
            "metadata": {"review_id": str(uuid4())},
        }
        
        collector.set_ai_review_result(ai_result)
        evidence = collector.collect()
        
        assert evidence.ai_review == ai_result

    def test_collector_without_ai_review(self):
        """未设置 AI 评审时 evidence.ai_review 为 None"""
        collector = TraceCollector(
            run_id=str(uuid4()),
            input_nl="Test scenario",
        )
        
        evidence = collector.collect()
        
        assert evidence.ai_review is None


class TestAIReviewResultToEvidence:
    """测试 AIReviewResult 转换为 Evidence 格式"""

    def test_ai_review_result_to_evidence_format(self):
        """AIReviewResult.to_evidence_format() 输出兼容 Evidence"""
        result = AIReviewResult(
            verdict=VerdictType.PASS,
            confidence=0.92,
            model_votes=[],
            reasoning="All good",
            metadata=AIMetadata(strategy_used=StrategyType.MAJORITY_VOTE),
        )
        
        evidence_format = result.to_evidence_format()
        
        assert "ai_review" in evidence_format
        assert evidence_format["ai_review"]["verdict"] == "PASS"
        assert evidence_format["ai_review"]["confidence"] == 0.92

    def test_full_integration_collector_with_ai_review(self):
        """完整集成：Collector + AIReviewResult"""
        # 1. 创建 AI 评审结果
        ai_config = AIReviewConfig(
            enabled=True,
            models=[
                ModelConfig(name="gpt-4", provider="openai"),
            ],
        )
        engine = AIReviewEngine(ai_config)
        ai_result = engine.review("test content")
        
        # 2. 创建 Collector 并设置结果
        collector = TraceCollector(
            run_id=str(uuid4()),
            input_nl="Run tests",
        )
        collector.set_ai_review_result(ai_result.to_evidence_format()["ai_review"])
        
        # 3. 收集 Evidence
        evidence = collector.collect()
        
        # 4. 验证
        assert evidence.ai_review is not None
        assert "verdict" in evidence.ai_review
        assert "confidence" in evidence.ai_review
        assert "model_votes" in evidence.ai_review
        assert "metadata" in evidence.ai_review


class TestEvidencePersistence:
    """测试 Evidence 持久化（保存和加载）"""

    def test_save_evidence_with_ai_review(self):
        """保存包含 AI 评审的 Evidence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = TraceCollector(
                run_id=str(uuid4()),
                input_nl="Test",
                artifact_root=Path(tmpdir),
            )
            
            ai_result = {
                "verdict": "PASS",
                "confidence": 0.9,
                "model_votes": [],
                "metadata": {"review_id": str(uuid4())},
            }
            collector.set_ai_review_result(ai_result)
            
            evidence, path = collector.collect_and_save()
            
            # 验证文件存在且内容正确
            assert path.exists()
            saved_data = json.loads(path.read_text())
            
            assert saved_data["ai_review"]["verdict"] == "PASS"
            assert saved_data["ai_review"]["confidence"] == 0.9


class TestEvidenceSchemaCompatibility:
    """测试 Evidence Schema 兼容性"""

    def test_ai_review_does_not_break_existing_fields(self):
        """AI 评审字段不影响现有字段"""
        evidence = Evidence(
            run_id=str(uuid4()),
            input_nl="Test",
            tool_calls=[
                ToolCallSummary(tool_name="run_pytest", status="success"),
            ],
            ai_review={"verdict": "PASS"},
        )
        
        data = evidence.model_dump(mode="json")
        
        assert data["run_id"] == evidence.run_id
        assert data["input_nl"] == "Test"
        assert len(data["tool_calls"]) == 1
        assert data["ai_review"]["verdict"] == "PASS"

    def test_evidence_round_trip(self):
        """Evidence 序列化和反序列化"""
        original = Evidence(
            run_id=str(uuid4()),
            input_nl="Test",
            ai_review={
                "verdict": "NEEDS_HITL",
                "confidence": 0.6,
                "hitl_triggered": True,
            },
        )
        
        # 序列化
        json_str = original.model_dump_json_for_file()
        
        # 反序列化
        loaded = Evidence.model_validate_json(json_str)
        
        assert loaded.run_id == original.run_id
        assert loaded.ai_review["verdict"] == "NEEDS_HITL"
        assert loaded.ai_review["hitl_triggered"] is True
