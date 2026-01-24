/**
 * 报告导出页面
 *
 * 支持导出执行记录为 Excel/JSON/CSV 格式
 */
import React, { useState } from "react";
import {
  Card,
  Button,
  Space,
  Select,
  DatePicker,
  Table,
  Tag,
} from "antd";
import { message } from "../components/AntdGlobal";
import {
  DownloadOutlined,
  FileExcelOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import axios from "axios";
import dayjs from "dayjs";

const { RangePicker } = DatePicker;

interface Execution {
  id: string;
  testcase_id: string;
  status: string;
  mode: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

const ReportExportPage: React.FC = () => {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(
    null
  );
  const [statusFilter, setStatusFilter] = useState<string | undefined>(
    undefined
  );
  const [exporting, setExporting] = useState(false);

  // 加载执行记录
  const loadExecutions = async () => {
    setLoading(true);
    try {
      const params: any = { page: 1, page_size: 100 };
      if (statusFilter) {
        params.status = statusFilter;
      }
      const response = await axios.get("/api/v1/executions", { params });
      let items = response.data.items || [];

      // 客户端日期过滤
      if (dateRange) {
        const [start, end] = dateRange;
        items = items.filter((item: Execution) => {
          const created = dayjs(item.created_at);
          return (
            created.isAfter(start.startOf("day")) &&
            created.isBefore(end.endOf("day"))
          );
        });
      }

      setExecutions(items);
    } catch (error) {
      message.error("加载失败");
    } finally {
      setLoading(false);
    }
  };

  // 导出为 JSON
  const exportJSON = () => {
    const data = JSON.stringify(executions, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    downloadBlob(blob, `test_report_${dayjs().format("YYYYMMDD_HHmmss")}.json`);
    message.success("JSON 导出成功");
  };

  // 导出为 CSV
  const exportCSV = () => {
    const headers = ["ID", "状态", "模式", "创建时间", "开始时间", "完成时间"];
    const rows = executions.map((e) => [
      e.id,
      e.status,
      e.mode,
      e.created_at,
      e.started_at || "",
      e.completed_at || "",
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(",")),
    ].join("\n");

    const blob = new Blob(["\ufeff" + csvContent], {
      type: "text/csv;charset=utf-8",
    });
    downloadBlob(blob, `test_report_${dayjs().format("YYYYMMDD_HHmmss")}.csv`);
    message.success("CSV 导出成功");
  };

  // 下载 Blob
  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getStatusTag = (status: string) => {
    const colors: Record<string, string> = {
      pending: "default",
      running: "processing",
      success: "success",
      failed: "error",
      stopped: "warning",
    };
    return (
      <Tag color={colors[status] || "default"}>{status.toUpperCase()}</Tag>
    );
  };

  const columns = [
    { title: "ID", dataIndex: "id", key: "id", width: 100, ellipsis: true },
    { title: "状态", dataIndex: "status", key: "status", render: getStatusTag },
    { title: "模式", dataIndex: "mode", key: "mode" },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (t: string) => dayjs(t).format("YYYY-MM-DD HH:mm:ss"),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2>导出测试报告</h2>

      {/* 筛选条件 */}
      <Card title="筛选条件" style={{ marginBottom: 16 }}>
        <Space wrap>
          <RangePicker
            value={dateRange}
            onChange={(dates) =>
              setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)
            }
            placeholder={["开始日期", "结束日期"]}
          />
          <Select
            style={{ width: 120 }}
            placeholder="执行状态"
            allowClear
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { label: "待执行", value: "pending" },
              { label: "运行中", value: "running" },
              { label: "成功", value: "success" },
              { label: "失败", value: "failed" },
              { label: "已停止", value: "stopped" },
            ]}
          />
          <Button type="primary" onClick={loadExecutions} loading={loading}>
            查询
          </Button>
        </Space>
      </Card>

      {/* 数据预览 */}
      <Card
        title={`数据预览 (${executions.length} 条)`}
        style={{ marginBottom: 16 }}
        extra={
          <Space>
            <Button
              icon={<FileTextOutlined />}
              onClick={exportJSON}
              disabled={executions.length === 0}
            >
              导出 JSON
            </Button>
            <Button
              icon={<FileExcelOutlined />}
              onClick={exportCSV}
              disabled={executions.length === 0}
            >
              导出 CSV
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={executions}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
};

export default ReportExportPage;
