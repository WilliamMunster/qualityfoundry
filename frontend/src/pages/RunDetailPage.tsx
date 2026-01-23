import React, { useEffect, useState } from 'react';
import { Typography, Card, Row, Col, Space, Button, message, Skeleton, Tag } from 'antd';
import { ChevronLeft, Share2, Download, Activity, FileJson, GitBranch } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import orchestrationsApi from '../api/orchestrations';
import EvidenceSplitter from '../components/EvidenceSplitter';
import AuditTimeline from '../components/AuditTimeline';
import NodeProgress from '../components/NodeProgress';
import ExecutionFlow from '../components/ExecutionFlow';
import { motion } from 'framer-motion';

const { Title, Text } = Typography;

const RunDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [evidence, setEvidence] = useState<any>(null);
  const [auditData, setAuditData] = useState<any[]>([]);

  // 从审计日志推断当前进度状态
  const getDerivedStatus = (events: any[]) => {
    if (!events.length) return 'POLICY_LOADED';
    const types = events.map(e => e.event_type);
    if (types.includes('DECISION_MADE')) return 'FINISHED';
    if (types.includes('TOOL_FINISHED')) return 'DECIDING';
    if (types.includes('TOOL_STARTED')) return 'EXECUTING';
    if (types.includes('PLAN_BUILT')) return 'EXECUTING';
    return 'PLAN_BUILT';
  };

  const fetchData = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [ev, au] = await Promise.all([
        orchestrationsApi.getEvidence(id),
        orchestrationsApi.getAudit(id)
      ]);
      setEvidence(ev);
      setAuditData(au.events);
    } catch (error) {
      console.error('Failed to fetch run details:', error);
      message.error('加载任务详情失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <Skeleton active avatar paragraph={{ rows: 12 }} />
      </div>
    );
  }

  const currentStatus = getDerivedStatus(auditData);

  return (
    <div style={{ padding: '4px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }}>
          <Space direction="vertical" size={2}>
            <Space>
              <Button
                type="text"
                icon={<ChevronLeft size={16} />}
                onClick={() => navigate('/runs')}
                style={{ marginLeft: -8 }}
              />
              <Title level={4} style={{ margin: 0 }}>分析详情</Title>
            </Space>
            <Space>
              <Text type="secondary" style={{ fontFamily: 'monospace' }}>{id}</Text>
              <Tag color={evidence?.decision === 'PASS' ? 'success' : 'error'} bordered={false}>
                {evidence?.decision || 'UNKNOWN'}
              </Tag>
            </Space>
          </Space>
        </motion.div>
        <Space>
          <Button icon={<Share2 size={16} />}>分享</Button>
          <Button
            type="primary"
            icon={<Download size={16} />}
            href={`/api/v1/artifacts/${id}/evidence.json`}
            download="evidence.json"
          >
            导出证据
          </Button>
        </Space>
      </div>

      <motion.div
        initial={{ y: 10, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        style={{ marginBottom: 24 }}
      >
        <NodeProgress currentStatus={currentStatus} />
      </motion.div>

      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.05 }}
        style={{ marginBottom: 24 }}
      >
        <Card
          variant="outlined"
          title={<Space><GitBranch size={18} className="text-purple-500" />过程追踪 (Flow Trace)</Space>}
          style={{ borderRadius: 20, boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)' }}
        >
          <ExecutionFlow events={auditData} />
        </Card>
      </motion.div>

      <Row gutter={24}>
        <Col span={16}>
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
          >
            <Card
              variant="outlined"
              title={<Space><FileJson size={18} className="text-indigo-500" />结构化证据 (Evidence)</Space>}
              style={{ borderRadius: 20, minHeight: 600, boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)' }}
            >
              <EvidenceSplitter evidence={evidence} runId={id!} />
            </Card>
          </motion.div>
        </Col>
        <Col span={8}>
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <Card
              variant="outlined"
              title={<Space><Activity size={18} className="text-emerald-500" />审计追踪 (Audit Log)</Space>}
              style={{ borderRadius: 20, boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)' }}
            >
              <div style={{ maxHeight: 'calc(100vh - 380px)', overflow: 'auto', padding: '12px 0' }}>
                <AuditTimeline events={auditData} />
              </div>
            </Card>
          </motion.div>
        </Col>
      </Row>
    </div>
  );
};

export default RunDetailPage;
