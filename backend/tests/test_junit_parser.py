"""Tests for JUnit XML Parser (PR-3)

验证 JUnit XML 解析的正确性。
"""

import tempfile
from pathlib import Path

import pytest

from qualityfoundry.governance.tracing.junit_parser import (
    parse_junit_xml,
    parse_junit_xml_content,
)


class TestParseJunitXml:
    """parse_junit_xml 测试"""

    def test_single_testsuite(self):
        """单个 testsuite"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="10" errors="1" failures="2" skipped="1" time="1.234">
    <testcase name="test_one" time="0.1"/>
</testsuite>'''

        summary = parse_junit_xml_content(content)

        assert summary["tests"] == 10
        assert summary["errors"] == 1
        assert summary["failures"] == 2
        assert summary["skipped"] == 1
        assert abs(summary["time"] - 1.234) < 0.001

    def test_multiple_testsuites(self):
        """多个 testsuites"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<testsuites>
    <testsuite name="suite1" tests="5" errors="0" failures="1" skipped="0" time="0.5">
    </testsuite>
    <testsuite name="suite2" tests="3" errors="1" failures="0" skipped="1" time="0.3">
    </testsuite>
</testsuites>'''

        summary = parse_junit_xml_content(content)

        assert summary["tests"] == 8  # 5 + 3
        assert summary["errors"] == 1  # 0 + 1
        assert summary["failures"] == 1  # 1 + 0
        assert summary["skipped"] == 1  # 0 + 1
        assert abs(summary["time"] - 0.8) < 0.001

    def test_testsuites_with_attributes(self):
        """testsuites 元素本身有属性（pytest 格式）"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<testsuites tests="10" errors="2" failures="3" skipped="1" time="2.5">
    <testsuite name="test" tests="10" errors="2" failures="3" skipped="1" time="2.5">
    </testsuite>
</testsuites>'''

        summary = parse_junit_xml_content(content)

        assert summary["tests"] == 10
        assert summary["errors"] == 2
        assert summary["failures"] == 3
        assert summary["skipped"] == 1

    def test_missing_attributes(self):
        """缺少属性时默认为 0"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" tests="5">
</testsuite>'''

        summary = parse_junit_xml_content(content)

        assert summary["tests"] == 5
        assert summary["errors"] == 0
        assert summary["failures"] == 0
        assert summary["skipped"] == 0
        assert summary["time"] == 0.0

    def test_empty_content(self):
        """空内容"""
        summary = parse_junit_xml_content("")
        assert summary["tests"] == 0
        assert summary["failures"] == 0

    def test_invalid_xml(self):
        """无效 XML（使用正则 fallback）"""
        content = 'not valid xml but has tests="5" failures="2"'

        summary = parse_junit_xml_content(content)

        assert summary["tests"] == 5
        assert summary["failures"] == 2

    def test_parse_from_file(self):
        """从文件解析"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<testsuite tests="3" failures="1" errors="0" skipped="0" time="0.123"/>'''

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w") as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            summary = parse_junit_xml(path)
            assert summary["tests"] == 3
            assert summary["failures"] == 1
        finally:
            path.unlink()

    def test_nonexistent_file(self):
        """不存在的文件"""
        summary = parse_junit_xml(Path("/nonexistent/junit.xml"))
        assert summary["tests"] == 0
        assert summary["failures"] == 0

    def test_pytest_format(self):
        """pytest 实际生成的格式"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<testsuites>
    <testsuite name="pytest" errors="0" failures="0" skipped="0" tests="4" time="0.051"
               timestamp="2024-01-01T00:00:00.000000" hostname="localhost">
        <testcase classname="test_sample" name="test_passing" time="0.001"/>
        <testcase classname="test_sample" name="test_another" time="0.001"/>
        <testcase classname="test_sample.TestClass" name="test_method_one" time="0.001"/>
        <testcase classname="test_sample.TestClass" name="test_method_two" time="0.001"/>
    </testsuite>
</testsuites>'''

        summary = parse_junit_xml_content(content)

        assert summary["tests"] == 4
        assert summary["failures"] == 0
        assert summary["errors"] == 0
