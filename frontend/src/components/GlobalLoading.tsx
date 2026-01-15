import React from 'react';
import { Spin, Typography } from 'antd';
import { useAppStore } from '../store';
import { LoadingOutlined } from '@ant-design/icons';

const { Text } = Typography;

const GlobalLoading: React.FC = () => {
  const { loading, loadingTip } = useAppStore();

  if (!loading) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        backdropFilter: 'blur(4px)',
        transition: 'all 0.3s ease-in-out',
      }}
    >
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center',
        gap: 24,
        padding: 40,
        borderRadius: 16,
        background: '#fff',
        boxShadow: '0 4px 20px rgba(0,0,0,0.08)'
      }}>
        <Spin 
          indicator={<LoadingOutlined style={{ fontSize: 48, color: '#1677ff' }} spin />} 
        />
        <div style={{ textAlign: 'center' }}>
          <Text strong style={{ fontSize: 18, color: '#1f1f1f' }}>
            {loadingTip || '加载中...'}
          </Text>
          <div style={{ marginTop: 8, height: 4, width: 200, background: '#f0f0f0', borderRadius: 2, overflow: 'hidden' }}>
            <div 
              style={{ 
                height: '100%', 
                background: '#1677ff', 
                width: '100%',
                animation: 'progress-loading 1.5s infinite ease-in-out'
              }} 
            />
          </div>
          <style>
            {`
              @keyframes progress-loading {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
              }
            `}
          </style>
        </div>
      </div>
    </div>
  );
};

export default GlobalLoading;
