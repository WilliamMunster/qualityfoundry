"""QualityFoundry - TestCase API Routes

测试用例管理 API 路由
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.models import (
    ApprovalStatus as DBApprovalStatus,
    TestCase,
    Scenario,
)
from qualityfoundry.models.testcase_schemas import (
    TestCaseCreate,
    TestCaseGenerateRequest,
    TestCaseListResponse,
    TestCaseResponse,
    TestCaseUpdate,
)
from qualityfoundry.services.approval_service import ApprovalService
from qualityfoundry.models.schemas import BatchDeleteRequest

router = APIRouter(prefix="/testcases", tags=["testcases"])


@router.post("/batch-delete", status_code=204)
def batch_delete_testcases(
    req: BatchDeleteRequest,
    db: Session = Depends(get_db)
):
    """批量删除测试用例"""
    db.query(TestCase).filter(TestCase.id.in_(req.ids)).delete(synchronize_session=False)
    db.commit()
    return None


@router.post("/generate", response_model=list[TestCaseResponse], status_code=201)
async def generate_testcases(
    req: TestCaseGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    AI 生成测试用例
    
    根据场景自动生成测试用例
    """
    # 1. 获取场景
    scenario = db.query(Scenario).filter(Scenario.id == req.scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="场景未找到")
    
    # 2. 调用 AI 服务
    from qualityfoundry.services.ai_service import AIService
    from qualityfoundry.database.ai_config_models import AIStep
    import json
    import traceback
    
    try:
        # 构建场景内容
        scenario_content = f"标题: {scenario.title}\n描述: {scenario.description or '无'}\n步骤:\n"
        for i, step in enumerate(scenario.steps or [], 1):
            scenario_content += f"{i}. {step}\n"
        
        # 定义变量注入模板
        prompt_variables = {"scenario": scenario_content}
        
        # 调用 AI
        response_content = await AIService.call_ai(
            db=db,
            step=AIStep.TESTCASE_GENERATION,
            prompt_variables=prompt_variables
        )
        
        # 清理 Markdown 代码块标记
        cleaned_content = response_content.strip()
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]
        if cleaned_content.startswith("```"):
            cleaned_content = cleaned_content[3:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
            
        testcases_data = json.loads(cleaned_content)
        
        # 3. 保存用例
        created_testcases = []
        for item in testcases_data:
            # 数据清洗
            title = str(item.get("title", "未命名用例"))
            
            raw_preconditions = item.get("preconditions", [])
            if isinstance(raw_preconditions, str):
                preconditions = [s.strip() for s in raw_preconditions.split('\n') if s.strip()]
            elif isinstance(raw_preconditions, list):
                preconditions = [str(s) for s in raw_preconditions]
            else:
                preconditions = []
            
            raw_steps = item.get("steps", [])
            steps = []
            expected_results = []
            
            if isinstance(raw_steps, list):
                for s in raw_steps:
                    if isinstance(s, dict):
                        # 核心重构：保留结构化对象
                        step_data = {
                            "step": str(s.get("step", "")),
                            "expected": str(s.get("expected", ""))
                        }
                        steps.append(step_data)
                        # 同时同步到旧的 expected_results 以防万一某些地方还在读它
                        expected_results.append(step_data["expected"])
                    else:
                        steps.append({"step": str(s), "expected": "见步骤说明"})
            elif isinstance(raw_steps, str):
                for s in raw_steps.split('\n'):
                    if s.strip():
                        steps.append({"step": s.strip(), "expected": "待补充"})
            
            # expected_results 可能不存在，从 steps 中提取
            raw_expected = item.get("expected_results", [])
            if isinstance(raw_expected, str):
                expected_results = [s.strip() for s in raw_expected.split('\n') if s.strip()]
            elif isinstance(raw_expected, list):
                expected_results = [str(s) for s in raw_expected]
            else:
                expected_results = []
            
            # 获取下一个 seq_id
            max_seq = db.query(func.max(TestCase.seq_id)).scalar() or 0
            
            testcase = TestCase(
                seq_id=max_seq + 1,
                scenario_id=req.scenario_id,
                title=title,
                preconditions=preconditions,
                steps=steps,
                expected_results=expected_results,
                approval_status=DBApprovalStatus.APPROVED if req.auto_approve else DBApprovalStatus.PENDING,
                version="v1.0"
            )
            db.add(testcase)
            db.flush()  # 确保 seq_id 被分配
            max_seq += 1  # 更新下一个 seq_id
            created_testcases.append(testcase)
            
        db.commit()
        
        for tc in created_testcases:
            db.refresh(tc)
            
            # 如果不是自动批准，创建审核记录
            if not req.auto_approve:
                approval_service = ApprovalService(db)
                approval_service.create_approval(
                    entity_type="testcase",
                    entity_id=tc.id
                )
        
        return created_testcases
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI 响应不是有效的 JSON 格式: {str(e)}")
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"AI TestCase Generation Error: {error_trace}")
        raise HTTPException(status_code=500, detail=f"AI 生成用例失败: {str(e)}")


@router.post("", response_model=TestCaseResponse, status_code=201)
def create_testcase(
    req: TestCaseCreate,
    db: Session = Depends(get_db)
):
    """创建测试用例"""
    # 生成 seq_id
    max_seq = db.query(func.max(TestCase.seq_id)).scalar() or 0
    
    testcase = TestCase(
        seq_id=max_seq + 1,
        scenario_id=req.scenario_id,
        title=req.title,
        preconditions=req.preconditions,
        # Pydantic 已经处理了 TestStep -> dict 的转换 (from_attributes=True / model_dump)
        steps=[s.model_dump() if hasattr(s, 'model_dump') else s for s in req.steps],
        expected_results=req.expected_results or [s.expected for s in req.steps if hasattr(s, 'expected')],
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
        # 转换为字典列表存储
        testcase.steps = [s.model_dump() if hasattr(s, 'model_dump') else s for s in req.steps]
        # 同步更新旧字段（可选）
        testcase.expected_results = [s.expected for s in req.steps if hasattr(s, 'expected')]
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
