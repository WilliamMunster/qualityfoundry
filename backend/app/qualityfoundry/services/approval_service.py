"""QualityFoundry - Approval Service

审核流程服务
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from qualityfoundry.database.models import (
    Approval,
    ApprovalStatus as DBApprovalStatus,
    Scenario,
    TestCase,
)
from qualityfoundry.services.notification_service import get_notification_service


class ApprovalService:
    """审核流程服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = get_notification_service()
    
    def create_approval(
        self,
        entity_type: str,
        entity_id: UUID,
        reviewer: Optional[str] = None
    ) -> Approval:
        """
        创建审核记录（幂等性：如果已存在 PENDING 记录，则返回现有记录）
        
        Args:
            entity_type: 实体类型（scenario/testcase/orchestration）
            entity_id: 实体 ID
            reviewer: 审核人（可选）
            
        Returns:
            审核记录
        """
        # 幂等性检查：查找是否已有待审核记录
        existing = self.db.query(Approval).filter(
            Approval.entity_type == entity_type,
            Approval.entity_id == entity_id,
            Approval.status == DBApprovalStatus.PENDING
        ).first()
        
        if existing:
            if reviewer:
                existing.reviewer = reviewer
                self.db.commit()
                self.db.refresh(existing)
            return existing

        approval = Approval(
            entity_type=entity_type,
            entity_id=entity_id,
            status=DBApprovalStatus.PENDING,
            reviewer=reviewer
        )
        
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        
        return approval
    
    def approve(
        self,
        approval_id: UUID,
        reviewer: str,
        comment: Optional[str] = None
    ) -> Approval:
        """
        批准审核
        
        Args:
            approval_id: 审核 ID
            reviewer: 审核人
            comment: 审核意见
            
        Returns:
            更新后的审核记录
        """
        approval = self.db.query(Approval).filter(Approval.id == approval_id).first()
        if not approval:
            raise ValueError(f"审核记录不存在: {approval_id}")
        
        if approval.status != DBApprovalStatus.PENDING:
            raise ValueError(f"审核状态不是待审核: {approval.status}")
        
        # 更新审核状态
        approval.status = DBApprovalStatus.APPROVED
        approval.reviewer = reviewer
        approval.review_comment = comment
        approval.reviewed_at = datetime.now(timezone.utc)
        
        # 更新关联实体的审核状态
        self._update_entity_status(approval.entity_type, approval.entity_id, DBApprovalStatus.APPROVED, reviewer)
        
        self.db.commit()
        self.db.refresh(approval)
        
        # 发送通知（异步，使用安全方式避免在同步上下文中失败）
        self._schedule_notification(
            event_type="approval_approved",
            entity_type=approval.entity_type,
            entity_id=str(approval.entity_id),
            status="approved",
            reviewer=reviewer,
            comment=comment
        )
        
        return approval
    
    def reject(
        self,
        approval_id: UUID,
        reviewer: str,
        comment: Optional[str] = None
    ) -> Approval:
        """
        拒绝审核
        
        Args:
            approval_id: 审核 ID
            reviewer: 审核人
            comment: 审核意见
            
        Returns:
            更新后的审核记录
        """
        approval = self.db.query(Approval).filter(Approval.id == approval_id).first()
        if not approval:
            raise ValueError(f"审核记录不存在: {approval_id}")
        
        if approval.status != DBApprovalStatus.PENDING:
            raise ValueError(f"审核状态不是待审核: {approval.status}")
        
        # 更新审核状态
        approval.status = DBApprovalStatus.REJECTED
        approval.reviewer = reviewer
        approval.review_comment = comment
        approval.reviewed_at = datetime.now(timezone.utc)
        
        # 更新关联实体的审核状态
        self._update_entity_status(approval.entity_type, approval.entity_id, DBApprovalStatus.REJECTED, reviewer)
        
        self.db.commit()
        self.db.refresh(approval)
        
        # 发送通知（异步，使用安全方式避免在同步上下文中失败）
        self._schedule_notification(
            event_type="approval_rejected",
            entity_type=approval.entity_type,
            entity_id=str(approval.entity_id),
            status="rejected",
            reviewer=reviewer,
            comment=comment
        )
        
        return approval
    
    def get_approval_history(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        status: Optional[DBApprovalStatus] = None
    ) -> list[Approval]:
        """
        获取审核历史
        
        Args:
            entity_type: 实体类型（可选）
            entity_id: 实体 ID（可选）
            status: 审核状态（可选）
            
        Returns:
            审核记录列表
        """
        query = self.db.query(Approval)
        
        if entity_type:
            query = query.filter(Approval.entity_type == entity_type)
        
        if entity_id:
            query = query.filter(Approval.entity_id == entity_id)
        
        if status:
            query = query.filter(Approval.status == status)
        
        return query.order_by(Approval.created_at.desc()).all()
    
    def batch_approve(
        self,
        entity_type: str,
        entity_ids: list[UUID],
        reviewer: str,
        comment: Optional[str] = None
    ) -> list[dict]:
        """
        批量批准审核
        
        Args:
            entity_type: 实体类型（scenario/testcase）
            entity_ids: 实体 ID 列表
            reviewer: 审核人
            comment: 审核意见
            
        Returns:
            批量操作结果列表
        """
        results = []
        
        for entity_id in entity_ids:
            try:
                # 查找待审核记录
                approval = self.db.query(Approval).filter(
                    Approval.entity_type == entity_type,
                    Approval.entity_id == entity_id,
                    Approval.status == DBApprovalStatus.PENDING
                ).first()
                
                if approval:
                    approval.status = DBApprovalStatus.APPROVED
                    approval.reviewer = reviewer
                    approval.review_comment = comment
                    approval.reviewed_at = datetime.now(timezone.utc)
                    self._update_entity_status(entity_type, entity_id, DBApprovalStatus.APPROVED, reviewer)
                    results.append({"entity_id": str(entity_id), "status": "approved", "success": True})
                else:
                    # 没有待审核记录，直接更新实体状态
                    self._update_entity_status(entity_type, entity_id, DBApprovalStatus.APPROVED, reviewer)
                    results.append({"entity_id": str(entity_id), "status": "approved", "success": True, "note": "直接审核"})
            except Exception as e:
                results.append({"entity_id": str(entity_id), "status": "error", "success": False, "error": str(e)})
        
        self.db.commit()
        return results
    
    def batch_reject(
        self,
        entity_type: str,
        entity_ids: list[UUID],
        reviewer: str,
        comment: Optional[str] = None
    ) -> list[dict]:
        """
        批量拒绝审核
        
        Args:
            entity_type: 实体类型（scenario/testcase）
            entity_ids: 实体 ID 列表
            reviewer: 审核人
            comment: 审核意见
            
        Returns:
            批量操作结果列表
        """
        results = []
        
        for entity_id in entity_ids:
            try:
                # 查找待审核记录
                approval = self.db.query(Approval).filter(
                    Approval.entity_type == entity_type,
                    Approval.entity_id == entity_id,
                    Approval.status == DBApprovalStatus.PENDING
                ).first()
                
                if approval:
                    approval.status = DBApprovalStatus.REJECTED
                    approval.reviewer = reviewer
                    approval.review_comment = comment
                    approval.reviewed_at = datetime.now(timezone.utc)
                    self._update_entity_status(entity_type, entity_id, DBApprovalStatus.REJECTED, reviewer)
                    results.append({"entity_id": str(entity_id), "status": "rejected", "success": True})
                else:
                    # 没有待审核记录，直接更新实体状态
                    self._update_entity_status(entity_type, entity_id, DBApprovalStatus.REJECTED, reviewer)
                    results.append({"entity_id": str(entity_id), "status": "rejected", "success": True, "note": "直接拒绝"})
            except Exception as e:
                results.append({"entity_id": str(entity_id), "status": "error", "success": False, "error": str(e)})
        
        self.db.commit()
        return results
    
    def _update_entity_status(
        self,
        entity_type: str,
        entity_id: UUID,
        status: DBApprovalStatus,
        reviewer: str
    ):
        """
        更新关联实体的审核状态
        
        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            status: 审核状态
            reviewer: 审核人
        """
        if entity_type == "scenario":
            entity = self.db.query(Scenario).filter(Scenario.id == entity_id).first()
        elif entity_type == "testcase":
            entity = self.db.query(TestCase).filter(TestCase.id == entity_id).first()
        else:
            raise ValueError(f"不支持的实体类型: {entity_type}")
        
        if entity:
            entity.approval_status = status
            entity.approved_by = reviewer if status == DBApprovalStatus.APPROVED else None
            entity.approved_at = datetime.now(timezone.utc) if status == DBApprovalStatus.APPROVED else None
    
    def _schedule_notification(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        status: str,
        reviewer: str,
        comment: Optional[str] = None
    ):
        """
        安全地调度通知任务
        
        在同步上下文中安全调用，不会因为没有事件循环而失败
        """
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_running_loop()
            # 如果有事件循环，创建任务
            loop.create_task(
                self.notification_service.send_approval_notification(
                    event_type=event_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    status=status,
                    reviewer=reviewer,
                    comment=comment
                )
            )
        except RuntimeError:
            # 没有事件循环（同步上下文），静默跳过通知
            # 在生产环境中可以使用线程或队列处理
            pass
