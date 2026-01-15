import React from 'react';
import { Spin } from 'antd';

interface LoadingProps {
  tip?: string;
  height?: number | string;
  fullScreen?: boolean;
}

const Loading: React.FC<LoadingProps> = ({ 
  tip = "加载中...", 
  height = "100%", 
  fullScreen = false 
}) => {
  if (fullScreen) {
    return (
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: 'rgba(255, 255, 255, 0.8)',
          zIndex: 9999,
          backdropFilter: 'blur(2px)'
        }}
      >
        <Spin size="large" tip={tip} />
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: height,
        width: '100%',
        minHeight: typeof height === 'number' ? height : 200
      }}
    >
      <Spin size="large" tip={tip} />
    </div>
  );
};

export default Loading;
