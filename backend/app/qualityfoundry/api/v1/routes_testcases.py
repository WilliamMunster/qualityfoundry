"""QualityFoundry - TestCase API Routes

测试用例管理 API 路由
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.models import (
    ApprovalStatus as DBApprovalStatus,
    TestCase,
)
from qualityfoundry.models.testcase_schemas import (
    TestCaseCreate,
    TestCaseGenerateRequest,
    TestCaseListResponse,
    TestCaseResponse,
    TestCaseUpdate,
)
from qualityfoundry.services.approval_service import ApprovalService

router = APIRouter(prefix="/testcases", tags=["testcases"])


@router.post("/generate", response_model=list[TestCaseResponse], status_code=201)
async def generate_testcases(
    req: TestCaseGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    AI 生成测试用例
    
    根据场景自动生成测试用例
    """
    # TODO: 集成 AI 生成服务
    # 目前返回示例用例
    
    testcase = TestCase(
        scenario_id=req.scenario_id,
        title="示例用例：用户登录成功",
        preconditions=["用户已注册", "用户未登录"],
        steps=["打开登录页面", "输入正确的用户名和密码", "点击登录按钮"],
        expected_results=["跳转到首页", "显示用户信息"],
        approval_status=DBApprovalStatus.APPROVED if req.auto_approve else DBApprovalStatus.PENDING,
        version="v1.0"
    )
    
    db.add(testcase)
    db.commit()
    db.refresh(testcase)
    
    # 如果不是自动批准，创建审核记录
    if not req.auto_approve:
        approval_service = ApprovalService(db)
        approval_service.create_approval(
            entity_type="testcase",
            entity_id=testcase.id
        )
    
    return [testcase]


@router.post("", response_model=TestCaseResponse, status_code=201)
def create_testcase(
    req: TestCaseCreate,
    db: Session = Depends(get_db)
):
    """创建测试用例"""
    testcase = TestCase(
        scenario_id=req.scenario_id,
        title=req.title,
        preconditions=req.preconditions,
        steps=req.steps,
        expected_results=req.expected_results,
        version="v1.0"
    )
    
    db.add(testcase)
    db.commit()
    db.refresh(testcase)
    
    return testcase


@router.get("", response_model=TestCaseListResponse)
def list_testcases(
    scenario_id: Optional[UUID] = None,
    approval_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """测试用例列表"""
    query = db.query(TestCase)
    
    # 按场景筛选
    if scenario_id:
        query = query.filter(TestCase.scenario_id == scenario_id)
    
    # 按审核状态筛选
    if approval_status:
        query = query.filter(TestCase.approval_status == approval_status)
    
    # 总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    items = query.order_by(TestCase.created_at.desc()).offset(offset).limit(page_size).all()
    
    return TestCaseListResponse(
        total=total,
        items=items,
        page=page,
        page_size=page_size
    )


@router.get("/{testcase_id}", response_model=TestCaseResponse)
def get_testcase(
    testcase_id: UUID,
    db: Session = Depends(get_db)
):
    """测试用例详情"""
    testcase = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not testcase:
        raise HTTPException(status_code=404, detail="TestCase not found")
    return testcase


@router.put("/{testcase_id}", response_model=TestCaseResponse)
def update_testcase(
    testcase_id: UUID,
    req: TestCaseUpdate,
    db: Session = Depends(get_db)
):
    """更新测试用例"""
    testcase = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not testcase:
        raise HTTPException(status_code=404, detail="TestCase not found")
    
    # 更新字段
    if req.title is not None:
        testcase.title = req.title
    if req.preconditions is not None:
        testcase.preconditions = req.preconditions
    if req.steps is not None:
        testcase.steps = req.steps
    if req.expected_results is not None:
        testcase.expected_results = req.expected_results
    
    db.commit()
    db.refresh(testcase)
    return testcase


@router.delete("/{testcase_id}", status_code=204)
def delete_testcase(
    testcase_id: UUID,
    db: Session = Depends(get_db)
):
    """删除测试用例"""
    testcase = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not testcase:
        raise HTTPException(status_code=404, detail="TestCase not found")
    
    db.delete(testcase)
    db.commit()
    return None


@router.post("/{testcase_id}/approve", response_model=TestCaseResponse)
def approve_testcase(
    testcase_id: UUID,
    reviewer: str,
    comment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """审核测试用例（批准）"""
    testcase = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not testcase:
        raise HTTPException(status_code=404, detail="TestCase not found")
    
    # 使用审核服务
    approval_service = ApprovalService(db)
    
    # 查找待审核记录
    approvals = approval_service.get_approval_history(
        entity_type="testcase",
        entity_id=testcase_id,
        status=DBApprovalStatus.PENDING
    )
    
    if not approvals:
        raise HTTPException(status_code=400, detail="没有待审核记录")
    
    # 批准第一个待审核记录
    approval_service.approve(
        approval_id=approvals[0].id,
        reviewer=reviewer,
        comment=comment
    )
    
    db.refresh(testcase)
    return testcase


@router.post("/{testcase_id}/reject", response_model=TestCaseResponse)
def reject_testcase(
    testcase_id: UUID,
    reviewer: str,
    comment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """审核测试用例（拒绝）"""
    testcase = db.query(TestCase).filter(TestCase.id == testcase_id).first()
    if not testcase:
        raise HTTPException(status_code=404, detail="TestCase not found")
    
    # 使用审核服务
    approval_service = ApprovalService(db)
    
    # 查找待审核记录
    approvals = approval_service.get_approval_history(
        entity_type="testcase",
        entity_id=testcase_id,
        status=DBApprovalStatus.PENDING
    )
    
    if not approvals:
        raise HTTPException(status_code=400, detail="没有待审核记录")
    
    # 拒绝第一个待审核记录
    approval_service.reject(
        approval_id=approvals[0].id,
        reviewer=reviewer,
        comment=comment
    )
    
    db.refresh(testcase)
    return testcase
