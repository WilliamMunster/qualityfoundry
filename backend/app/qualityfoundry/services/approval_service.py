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
        创建审核记录
        
        Args:
            entity_type: 实体类型（scenario/testcase）
            entity_id: 实体 ID
            reviewer: 审核人（可选）
            
        Returns:
            审核记录
        """
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
        
        # 发送通知（异步）
        asyncio.create_task(
            self.notification_service.send_approval_notification(
                event_type="approval_approved",
                entity_type=approval.entity_type,
                entity_id=str(approval.entity_id),
                status="approved",
                reviewer=reviewer,
                comment=comment
            )
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
        
        # 发送通知（异步）
        asyncio.create_task(
            self.notification_service.send_approval_notification(
                event_type="approval_rejected",
                entity_type=approval.entity_type,
                entity_id=str(approval.entity_id),
                status="rejected",
                reviewer=reviewer,
                comment=comment
            )
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
