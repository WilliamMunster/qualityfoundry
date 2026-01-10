"""QualityFoundry - WebSocket API Routes

WebSocket 实时推送端点
"""
import asyncio
import logging
from typing import Dict, Set
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from qualityfoundry.services.execution.async_executor import get_task_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # execution_id -> set of websocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, execution_id: str):
        """建立连接"""
        await websocket.accept()
        async with self._lock:
            if execution_id not in self._connections:
                self._connections[execution_id] = set()
            self._connections[execution_id].add(websocket)
        logger.info(f"WebSocket 连接建立: execution={execution_id}")
    
    async def disconnect(self, websocket: WebSocket, execution_id: str):
        """断开连接"""
        async with self._lock:
            if execution_id in self._connections:
                self._connections[execution_id].discard(websocket)
                if not self._connections[execution_id]:
                    del self._connections[execution_id]
        logger.info(f"WebSocket 连接断开: execution={execution_id}")
    
    async def broadcast(self, execution_id: str, message: dict):
        """向指定执行的所有连接广播消息"""
        async with self._lock:
            connections = self._connections.get(execution_id, set()).copy()
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"WebSocket 发送失败: {e}")


# 全局连接管理器
manager = ConnectionManager()


@router.websocket("/executions/{execution_id}")
async def execution_progress_ws(websocket: WebSocket, execution_id: str):
    """
    执行进度 WebSocket 端点
    
    客户端连接后，将持续推送执行进度更新，直到执行完成或连接断开
    """
    await manager.connect(websocket, execution_id)
    
    try:
        task_manager = get_task_manager()
        
        while True:
            # 获取当前进度
            task_info = await task_manager.get_task_by_execution(UUID(execution_id))
            
            if task_info:
                message = {
                    "type": "progress",
                    "execution_id": execution_id,
                    "status": task_info.progress.status.value,
                    "progress": task_info.progress.progress,
                    "current_step": task_info.progress.current_step,
                    "message": task_info.progress.message,
                    "logs": task_info.logs[-10:],  # 最近 10 条日志
                }
                
                await websocket.send_json(message)
                
                # 如果任务已完成，发送完成消息并关闭连接
                if task_info.progress.status.value in ["success", "failed", "stopped"]:
                    await websocket.send_json({
                        "type": "complete",
                        "execution_id": execution_id,
                        "status": task_info.progress.status.value,
                        "result": task_info.result,
                    })
                    break
            else:
                # 任务不存在，发送错误消息
                await websocket.send_json({
                    "type": "error",
                    "execution_id": execution_id,
                    "message": "任务未找到",
                })
            
            # 等待 1 秒后再次查询
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket 客户端断开: execution={execution_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "execution_id": execution_id,
                "message": str(e),
            })
        except Exception:
            pass
    finally:
        await manager.disconnect(websocket, execution_id)
