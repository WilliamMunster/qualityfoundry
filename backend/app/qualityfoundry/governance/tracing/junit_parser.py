"""QualityFoundry - JUnit XML Parser

解析 JUnit XML 报告，提取测试统计信息。

支持格式：
- 单 <testsuite> 格式
- 多 <testsuites> 包装格式
- pytest 生成的 JUnit XML
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)


class JUnitSummary(TypedDict):
    """JUnit 测试统计摘要"""
    tests: int
    failures: int
    errors: int
    skipped: int
    time: float


def parse_junit_xml(path: Path | str) -> JUnitSummary:
    """解析 JUnit XML 文件，提取测试统计

    Args:
        path: JUnit XML 文件路径

    Returns:
        JUnitSummary: 测试统计摘要

    Note:
        - 兼容 <testsuite> 和 <testsuites> 格式
        - 缺失字段默认为 0
        - 解析失败返回全零摘要
    """
    path = Path(path)

    if not path.exists():
        logger.warning(f"JUnit XML file not found: {path}")
        return _empty_summary()

    try:
        content = path.read_text(encoding="utf-8")
        return parse_junit_xml_content(content)
    except Exception as e:
        logger.warning(f"Failed to parse JUnit XML {path}: {e}")
        return _empty_summary()


def parse_junit_xml_content(content: str) -> JUnitSummary:
    """解析 JUnit XML 内容字符串

    Args:
        content: JUnit XML 内容

    Returns:
        JUnitSummary: 测试统计摘要
    """
    if not content.strip():
        return _empty_summary()

    try:
        root = ET.fromstring(content)
        return _parse_element(root)
    except ET.ParseError as e:
        logger.warning(f"XML parse error: {e}")
        # 尝试正则解析作为 fallback
        return _parse_with_regex(content)


def _parse_element(root: ET.Element) -> JUnitSummary:
    """从 XML 元素解析统计信息"""
    # 判断是 testsuites 还是 testsuite
    if root.tag == "testsuites":
        # 聚合所有 testsuite
        return _aggregate_testsuites(root)
    elif root.tag == "testsuite":
        return _parse_testsuite(root)
    else:
        # 尝试查找 testsuite 子元素
        testsuite = root.find(".//testsuite")
        if testsuite is not None:
            return _parse_testsuite(testsuite)
        return _empty_summary()


def _parse_testsuite(elem: ET.Element) -> JUnitSummary:
    """解析单个 testsuite 元素"""
    return JUnitSummary(
        tests=_get_int_attr(elem, "tests"),
        failures=_get_int_attr(elem, "failures"),
        errors=_get_int_attr(elem, "errors"),
        skipped=_get_int_attr(elem, "skipped") or _get_int_attr(elem, "skip"),
        time=_get_float_attr(elem, "time"),
    )


def _aggregate_testsuites(root: ET.Element) -> JUnitSummary:
    """聚合多个 testsuite 的统计"""
    total = JUnitSummary(tests=0, failures=0, errors=0, skipped=0, time=0.0)

    for testsuite in root.findall("testsuite"):
        suite_summary = _parse_testsuite(testsuite)
        total["tests"] += suite_summary["tests"]
        total["failures"] += suite_summary["failures"]
        total["errors"] += suite_summary["errors"]
        total["skipped"] += suite_summary["skipped"]
        total["time"] += suite_summary["time"]

    # 如果 testsuites 本身有属性，使用它们（pytest 有时直接写在 testsuites 上）
    if root.get("tests"):
        return JUnitSummary(
            tests=_get_int_attr(root, "tests"),
            failures=_get_int_attr(root, "failures"),
            errors=_get_int_attr(root, "errors"),
            skipped=_get_int_attr(root, "skipped"),
            time=_get_float_attr(root, "time"),
        )

    return total


def _get_int_attr(elem: ET.Element, name: str) -> int:
    """获取整数属性，缺失返回 0"""
    val = elem.get(name)
    if val is None:
        return 0
    try:
        return int(val)
    except ValueError:
        return 0


def _get_float_attr(elem: ET.Element, name: str) -> float:
    """获取浮点数属性，缺失返回 0.0"""
    val = elem.get(name)
    if val is None:
        return 0.0
    try:
        return float(val)
    except ValueError:
        return 0.0


def _parse_with_regex(content: str) -> JUnitSummary:
    """使用正则表达式解析（XML 解析失败时的 fallback）"""
    summary = _empty_summary()

    patterns = [
        (r'tests="(\d+)"', "tests", int),
        (r'failures="(\d+)"', "failures", int),
        (r'errors="(\d+)"', "errors", int),
        (r'skipped="(\d+)"', "skipped", int),
        (r'time="([\d.]+)"', "time", float),
    ]

    for pattern, key, converter in patterns:
        match = re.search(pattern, content)
        if match:
            try:
                summary[key] = converter(match.group(1))
            except ValueError:
                pass

    return summary


def _empty_summary() -> JUnitSummary:
    """返回空的统计摘要"""
    return JUnitSummary(tests=0, failures=0, errors=0, skipped=0, time=0.0)
