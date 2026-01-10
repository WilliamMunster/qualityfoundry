/**
 * WebSocket 客户端 Hook
 * 
 * 用于订阅执行进度实时更新
 */
import { useEffect, useRef, useState, useCallback } from 'react';

export interface ExecutionProgress {
    type: 'progress' | 'complete' | 'error';
    execution_id: string;
    status?: string;
    progress?: number | null;
    current_step?: string | null;
    message?: string | null;
    logs?: string[];
    result?: any;
}

interface UseExecutionWebSocketOptions {
    onProgress?: (data: ExecutionProgress) => void;
    onComplete?: (data: ExecutionProgress) => void;
    onError?: (error: string) => void;
    autoConnect?: boolean;
}

export function useExecutionWebSocket(
    executionId: string | null,
    options: UseExecutionWebSocketOptions = {}
) {
    const { onProgress, onComplete, onError, autoConnect = true } = options;
    const [connected, setConnected] = useState(false);
    const [lastProgress, setLastProgress] = useState<ExecutionProgress | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<number | null>(null);

    const connect = useCallback(() => {
        if (!executionId) return;

        // 关闭已有连接
        if (wsRef.current) {
            wsRef.current.close();
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.hostname}:8000/api/v1/ws/executions/${executionId}`;

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('WebSocket 连接已建立');
                setConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const data: ExecutionProgress = JSON.parse(event.data);
                    setLastProgress(data);

                    switch (data.type) {
                        case 'progress':
                            onProgress?.(data);
                            break;
                        case 'complete':
                            onComplete?.(data);
                            ws.close();
                            break;
                        case 'error':
                            onError?.(data.message || '未知错误');
                            break;
                    }
                } catch (e) {
                    console.error('WebSocket 消息解析失败:', e);
                }
            };

            ws.onclose = () => {
                console.log('WebSocket 连接已关闭');
                setConnected(false);
                wsRef.current = null;
            };

            ws.onerror = (error) => {
                console.error('WebSocket 错误:', error);
                onError?.('WebSocket 连接错误');
            };
        } catch (e) {
            console.error('WebSocket 创建失败:', e);
            onError?.('无法创建 WebSocket 连接');
        }
    }, [executionId, onProgress, onComplete, onError]);

    const disconnect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
    }, []);

    useEffect(() => {
        if (autoConnect && executionId) {
            connect();
        }

        return () => {
            disconnect();
        };
    }, [autoConnect, executionId, connect, disconnect]);

    return {
        connected,
        lastProgress,
        connect,
        disconnect,
    };
}

export default useExecutionWebSocket;
