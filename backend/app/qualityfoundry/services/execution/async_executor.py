"""QualityFoundry - Async Execution Task Manager

异步执行任务管理器

设计原则：
- 抽象接口 + 具体实现，便于后续扩展
- 内存版本用于开发/测试
- 预留 Redis/Celery 扩展点
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class TaskProgress:
    """任务进度"""
    status: TaskStatus = TaskStatus.PENDING
    progress: Optional[int] = None  # 0-100
    current_step: Optional[str] = None
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: UUID
    execution_id: UUID
    progress: TaskProgress = field(default_factory=TaskProgress)
    logs: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    _task: Optional[asyncio.Task] = None  # 内部使用


class ExecutionTaskManagerBase(ABC):
    """
    执行任务管理器抽象基类
    
    扩展点：
    - 实现子类可使用 Redis/Celery/RQ 等
    - 只需实现抽象方法即可替换
    """
    
    @abstractmethod
    async def submit_task(
        self,
        execution_id: UUID,
        executor_func: Callable,
        *args,
        **kwargs
    ) -> UUID:
        """提交任务并返回任务 ID"""
        pass
    
    @abstractmethod
    async def get_task_info(self, task_id: UUID) -> Optional[TaskInfo]:
        """获取任务信息"""
        pass
    
    @abstractmethod
    async def cancel_task(self, task_id: UUID) -> bool:
        """取消任务"""
        pass
    
    @abstractmethod
    async def get_task_logs(self, task_id: UUID) -> List[str]:
        """获取任务日志"""
        pass
    
    @abstractmethod
    def update_progress(
        self,
        task_id: UUID,
        progress: int,
        current_step: str,
        message: Optional[str] = None
    ) -> None:
        """更新任务进度（供执行器回调）"""
        pass
    
    @abstractmethod
    def add_log(self, task_id: UUID, log: str) -> None:
        """添加日志（供执行器回调）"""
        pass


class InMemoryTaskManager(ExecutionTaskManagerBase):
    """
    内存版任务管理器
    
    特点：
    - 使用 asyncio.create_task 实现异步执行
    - 状态存储在内存中
    - 适合开发/测试环境
    - 重启后状态丢失
    """
    
    def __init__(self, max_concurrent: int = 10):
        self._tasks: Dict[UUID, TaskInfo] = {}
        self._execution_to_task: Dict[UUID, UUID] = {}  # execution_id -> task_id
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()
    
    async def submit_task(
        self,
        execution_id: UUID,
        executor_func: Callable,
        *args,
        **kwargs
    ) -> UUID:
        """提交任务"""
        import uuid
        task_id = uuid.uuid4()
        
        task_info = TaskInfo(
            task_id=task_id,
            execution_id=execution_id,
            progress=TaskProgress(status=TaskStatus.PENDING)
        )
        
        async with self._lock:
            self._tasks[task_id] = task_info
            self._execution_to_task[execution_id] = task_id
        
        # 创建后台任务
        asyncio_task = asyncio.create_task(
            self._run_task(task_id, executor_func, *args, **kwargs)
        )
        task_info._task = asyncio_task
        
        logger.info(f"任务已提交: {task_id} (execution: {execution_id})")
        return task_id
    
    async def _run_task(
        self,
        task_id: UUID,
        executor_func: Callable,
        *args,
        **kwargs
    ) -> None:
        """运行任务（内部方法）"""
        task_info = self._tasks.get(task_id)
        if not task_info:
            return
        
        async with self._semaphore:
            task_info.progress.status = TaskStatus.RUNNING
            task_info.progress.started_at = datetime.now(timezone.utc)
            self.add_log(task_id, f"任务开始执行: {datetime.now(timezone.utc).isoformat()}")
            
            try:
                # 注入回调函数
                kwargs['_task_manager'] = self
                kwargs['_task_id'] = task_id
                
                # 执行任务
                if asyncio.iscoroutinefunction(executor_func):
                    result = await executor_func(*args, **kwargs)
                else:
                    # 同步函数在线程池中执行
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, lambda: executor_func(*args, **kwargs)
                    )
                
                task_info.result = result
                task_info.progress.status = TaskStatus.SUCCESS
                task_info.progress.progress = 100
                self.add_log(task_id, f"任务执行成功: {datetime.now(timezone.utc).isoformat()}")
                
            except asyncio.CancelledError:
                task_info.progress.status = TaskStatus.STOPPED
                task_info.progress.message = "任务被用户取消"
                self.add_log(task_id, f"任务被取消: {datetime.now(timezone.utc).isoformat()}")
                
            except Exception as e:
                task_info.progress.status = TaskStatus.FAILED
                task_info.progress.error = str(e)
                self.add_log(task_id, f"任务执行失败: {str(e)}")
                logger.error(f"任务 {task_id} 执行失败: {e}")
                
            finally:
                task_info.progress.completed_at = datetime.now(timezone.utc)
    
    async def get_task_info(self, task_id: UUID) -> Optional[TaskInfo]:
        """获取任务信息"""
        return self._tasks.get(task_id)
    
    async def get_task_by_execution(self, execution_id: UUID) -> Optional[TaskInfo]:
        """通过 execution_id 获取任务信息"""
        task_id = self._execution_to_task.get(execution_id)
        if task_id:
            return self._tasks.get(task_id)
        return None
    
    async def cancel_task(self, task_id: UUID) -> bool:
        """取消任务"""
        task_info = self._tasks.get(task_id)
        if not task_info:
            return False
        
        if task_info._task and not task_info._task.done():
            task_info._task.cancel()
            logger.info(f"任务已取消: {task_id}")
            return True
        
        return False
    
    async def cancel_by_execution(self, execution_id: UUID) -> bool:
        """通过 execution_id 取消任务"""
        task_id = self._execution_to_task.get(execution_id)
        if task_id:
            return await self.cancel_task(task_id)
        return False
    
    async def get_task_logs(self, task_id: UUID) -> List[str]:
        """获取任务日志"""
        task_info = self._tasks.get(task_id)
        if task_info:
            return task_info.logs.copy()
        return []
    
    async def get_logs_by_execution(self, execution_id: UUID) -> List[str]:
        """通过 execution_id 获取日志"""
        task_id = self._execution_to_task.get(execution_id)
        if task_id:
            return await self.get_task_logs(task_id)
        return []
    
    def update_progress(
        self,
        task_id: UUID,
        progress: int,
        current_step: str,
        message: Optional[str] = None
    ) -> None:
        """更新任务进度"""
        task_info = self._tasks.get(task_id)
        if task_info:
            task_info.progress.progress = progress
            task_info.progress.current_step = current_step
            task_info.progress.message = message
    
    def add_log(self, task_id: UUID, log: str) -> None:
        """添加日志"""
        task_info = self._tasks.get(task_id)
        if task_info:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            task_info.logs.append(f"[{timestamp}] {log}")


# 全局任务管理器实例
_task_manager: Optional[ExecutionTaskManagerBase] = None


def get_task_manager() -> ExecutionTaskManagerBase:
    """
    获取全局任务管理器
    
    扩展点：可以通过环境变量或配置切换实现
    例如: TASK_MANAGER=redis 则使用 RedisTaskManager
    """
    global _task_manager
    
    if _task_manager is None:
        # 默认使用内存版本
        # 后续可根据配置切换：
        # if settings.task_manager == "redis":
        #     _task_manager = RedisTaskManager()
        # elif settings.task_manager == "celery":
        #     _task_manager = CeleryTaskManager()
        _task_manager = InMemoryTaskManager()
        logger.info("使用内存版任务管理器 (InMemoryTaskManager)")
    
    return _task_manager


def set_task_manager(manager: ExecutionTaskManagerBase) -> None:
    """
    设置全局任务管理器（用于测试或切换实现）
    """
    global _task_manager
    _task_manager = manager
