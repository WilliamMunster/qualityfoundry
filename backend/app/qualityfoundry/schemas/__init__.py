"""QualityFoundry - Schema Definitions

结构化数据模式的集中定义，包括：
- Evidence Schema v1
- JSON Schema 校验工具
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Schema 文件路径
SCHEMAS_DIR = Path(__file__).parent
EVIDENCE_SCHEMA_V1_PATH = SCHEMAS_DIR / "evidence.v1.schema.json"


def load_evidence_schema_v1() -> dict[str, Any]:
    """加载 Evidence Schema v1"""
    with open(EVIDENCE_SCHEMA_V1_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_evidence_v1(evidence: dict[str, Any]) -> None:
    """校验 evidence 是否符合 v1 schema
    
    Args:
        evidence: 待校验的证据字典
        
    Raises:
        EvidenceValidationError: 校验失败时抛出
        
    Example:
        >>> evidence = load_evidence(run_id)
        >>> validate_evidence_v1(evidence.model_dump())
    """
    from jsonschema import validate, ValidationError as JsonSchemaValidationError
    
    schema = load_evidence_schema_v1()
    
    try:
        validate(instance=evidence, schema=schema)
    except JsonSchemaValidationError as e:
        raise EvidenceValidationError(
            f"Evidence validation failed: {e.message} at {list(e.path)}"
        ) from e


def validate_evidence_v1_silent(evidence: dict[str, Any]) -> tuple[bool, list[str]]:
    """静默校验 evidence，返回校验结果和错误列表
    
    Args:
        evidence: 待校验的证据字典
        
    Returns:
        (是否通过, 错误信息列表)
        
    Example:
        >>> valid, errors = validate_evidence_v1_silent(evidence)
        >>> if not valid:
        ...     logger.warning(f"Evidence validation failed: {errors}")
    """
    from jsonschema import validate, ValidationError as JsonSchemaValidationError
    
    schema = load_evidence_schema_v1()
    errors = []
    
    try:
        validate(instance=evidence, schema=schema)
        return True, []
    except JsonSchemaValidationError as e:
        errors.append(f"{e.message} at {list(e.path)}")
        # 继续检查其他错误
        if e.context:
            for ctx in e.context:
                errors.append(f"{ctx.message} at {list(ctx.path)}")
        return False, errors


class EvidenceValidationError(Exception):
    """Evidence 校验错误"""
    pass


class EvidenceSchemaVersion(BaseModel):
    """Evidence Schema 版本信息"""
    
    version: str = "1.0.0"
    schema_uri: str = "https://qualityfoundry.ai/schemas/evidence.v1.schema.json"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": self.schema_uri,
            "schema_version": self.version,
        }


# 全局 schema 版本实例
EVIDENCE_SCHEMA_V1 = EvidenceSchemaVersion()


__all__ = [
    "EVIDENCE_SCHEMA_V1",
    "EVIDENCE_SCHEMA_V1_PATH",
    "EvidenceSchemaVersion",
    "EvidenceValidationError",
    "load_evidence_schema_v1",
    "validate_evidence_v1",
    "validate_evidence_v1_silent",
]
