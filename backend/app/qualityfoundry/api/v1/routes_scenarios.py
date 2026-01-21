"""QualityFoundry - Scenario API Routes

场景管理 API 路由
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from qualityfoundry.database.config import get_db
from qualityfoundry.database.models import (
    ApprovalStatus as DBApprovalStatus,
    Scenario,
    Requirement,
    TestCase,
)
from qualityfoundry.models.scenario_schemas import (
    ScenarioCreate,
    ScenarioGenerateRequest,
    ScenarioListResponse,
    ScenarioResponse,
    ScenarioUpdate,
)
from qualityfoundry.services.approval_service import ApprovalService
from qualityfoundry.models.schemas import BatchDeleteRequest
from qualityfoundry.models.approval_schemas import (
    BatchApprovalRequest,
    BatchApprovalResponse,
    BatchApprovalResult,
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("/batch-delete", status_code=204)
def batch_delete_scenarios(
    req: BatchDeleteRequest,
    db: Session = Depends(get_db)
):
    """批量删除场景"""
    # 检查是否有关联的测试用例
    scenarios_with_testcases = db.query(Scenario.id, Scenario.seq_id).filter(
        Scenario.id.in_(req.ids)
    ).join(TestCase, Scenario.id == TestCase.scenario_id).distinct().all()

    if scenarios_with_testcases:
        seq_ids = [s.seq_id for s in scenarios_with_testcases]
        raise HTTPException(
            status_code=400,
            detail=f"场景 {seq_ids} 下存在关联的测试用例，请先删除测试用例后再删除场景"
        )

    db.query(Scenario).filter(Scenario.id.in_(req.ids)).delete(synchronize_session=False)
    db.commit()
    return None


@router.post("/generate", response_model=list[ScenarioResponse], status_code=201)
async def generate_scenarios(
    req: ScenarioGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    AI 生成场景
    
    根据需求文档自动生成测试场景
    """
    # 1. 获取需求
    # 1. 获取需求
    print(f"[DEBUG] Searching for requirement_id: {req.requirement_id}")
    requirement = db.query(Requirement).filter(Requirement.id == req.requirement_id).first()
    if not requirement:
        print(f"[DEBUG] Requirement NOT FOUND: {req.requirement_id}")
        all_reqs = db.query(Requirement).all()
        print(f"[DEBUG] Available requirements: {[str(r.id) for r in all_reqs]}")
        raise HTTPException(status_code=404, detail="需求未找到")
    print(f"[DEBUG] Found requirement: {requirement.title}")
        
    # [FIX] 检查内容是否为占位符（由于之前缺少 python-docx 导致）
    if requirement.content and "需要安装 python-docx 库" in requirement.content and requirement.file_path:
        try:
            from qualityfoundry.services.file_upload import file_upload_service
            import os
            
            # 确保文件存在
            if os.path.exists(requirement.file_path):
                # 重新提取文本
                print(f"检测到占位符内容，尝试重新从 {requirement.file_path} 提取文本...")
                new_content = file_upload_service.extract_text(requirement.file_path)
                
                # 如果提取成功且不再是占位符，更新数据库
                if new_content and "需要安装 python-docx 库" not in new_content:
                    requirement.content = new_content
                    db.commit()
                    db.refresh(requirement)
                    print("文本重新提取成功并已更新到数据库")
        except Exception as e:
            print(f"尝试重新提取文本失败: {e}")
            # 继续执行，可能会因为内容无效而失败，但至少尝试过了

        
    # 2. 调用 AI 服务
    from qualityfoundry.services.ai_service import AIService, validate_scenario_response
    from qualityfoundry.database.ai_config_models import AIStep
    import json
    import traceback
    
    import logging
    logger = logging.getLogger("qualityfoundry.api.scenarios")
    
    try:
        # 定义包含 ID 的需求文本
        requirement_text = f"需求 ID: REQ-{requirement.seq_id}\n需求标题: {requirement.title}\n需求内容: {requirement.content}"
        
        # 调用 AI
        logger.info(f"Calling AI for scenario generation (requirement_id: {req.requirement_id})")
        response_content = await AIService.call_ai(
            db=db,
            step=AIStep.SCENARIO_GENERATION,
            prompt_variables={"requirement": requirement_text},
            config_id=req.config_id
        )
        
        # 调试输出
        logger.info(f"AI returned response of length {len(response_content)}")
        
        import re
        # 提取 JSON 数组内容
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response_content, re.DOTALL)
        if json_match:
            cleaned_content = json_match.group(0)
        else:
            cleaned_content = response_content.strip()
            # 基础剥离
            if "```json" in cleaned_content:
                cleaned_content = cleaned_content.split("```json")[-1].split("```")[0].strip()
            elif "```" in cleaned_content:
                cleaned_content = cleaned_content.split("```")[-1].split("```")[0].strip()
        
        try:
            scenarios_data = json.loads(cleaned_content)
            if not isinstance(scenarios_data, list):
                if isinstance(scenarios_data, dict):
                    scenarios_data = [scenarios_data]
                else:
                    raise ValueError("Parsed JSON is not a list or dictionary")
        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}. Content: {cleaned_content[:200]}")
            raise HTTPException(status_code=500, detail=f"AI 返回格式解析失败: {str(e)}")
            
        # 3. 保存场景
        logger.info(f"Saving {len(scenarios_data)} scenarios to DB...")
        created_scenarios = []
        
        # 预先获取当前最大 seq_id
        current_max_seq = db.query(func.max(Scenario.seq_id)).scalar() or 0
        
        for i, item in enumerate(scenarios_data):
            # 数据清洗与容错
            title = str(item.get("title", f"未命名场景 {i+1}"))
            description = str(item.get("description", "")) if item.get("description") else None
            
            raw_steps = item.get("steps", [])
            if isinstance(raw_steps, str):
                steps = [s.strip() for s in raw_steps.split('\n') if s.strip()]
            elif isinstance(raw_steps, list):
                steps = [str(s) for s in raw_steps]
            else:
                steps = []
            
            scenario = Scenario(
                seq_id=current_max_seq + 1,
                requirement_id=req.requirement_id,
                requirement=requirement,
                title=title,
                description=description,
                steps=steps,
                approval_status=DBApprovalStatus.APPROVED if req.auto_approve else DBApprovalStatus.PENDING,
                version="v1.0"
            )
            db.add(scenario)
            current_max_seq += 1
            created_scenarios.append(scenario)
            
        db.commit()
        logger.info(f"Successfully committed {len(created_scenarios)} scenarios.")
        
        for s in created_scenarios:
            db.refresh(s)
            
            # 如果不是自动批准，创建审核记录
            if not req.auto_approve:
                approval_service = ApprovalService(db)
                approval_service.create_approval(
                    entity_type="scenario",
                    entity_id=s.id
                )
        
        return created_scenarios
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"AI 响应不是有效的 JSON 格式: {str(e)}")
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"AI Generation Error: {error_trace}")
        raise HTTPException(status_code=500, detail=f"AI 生成失败: {str(e)} | {error_trace}")


@router.post("", response_model=ScenarioResponse, status_code=201)
def create_scenario(
    req: ScenarioCreate,
    db: Session = Depends(get_db)
):
    """创建场景"""
    # 生成 seq_id
    max_seq = db.query(func.max(Scenario.seq_id)).scalar() or 0
    
    scenario = Scenario(
        seq_id=max_seq + 1,
        requirement_id=req.requirement_id,
        title=req.title,
        description=req.description,
        steps=req.steps,
        version="v1.0"
    )
    
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    return scenario


@router.get("", response_model=ScenarioListResponse)
def list_scenarios(
    requirement_id: Optional[UUID] = None,
    approval_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """场景列表"""
    from sqlalchemy.orm import joinedload
    query = db.query(Scenario).options(joinedload(Scenario.requirement))
    
    # 按需求筛选
    if requirement_id:
        query = query.filter(Scenario.requirement_id == requirement_id)
    
    # 按审核状态筛选
    if approval_status:
        query = query.filter(Scenario.approval_status == approval_status)
    
    # 总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    items = query.order_by(Scenario.created_at.desc()).offset(offset).limit(page_size).all()
    
    return ScenarioListResponse(
        total=total,
        items=items,
        page=page,
        page_size=page_size
    )


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: UUID,
    db: Session = Depends(get_db)
):
    """场景详情"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: UUID,
    req: ScenarioUpdate,
    db: Session = Depends(get_db)
):
    """更新场景"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # 更新字段
    if req.title is not None:
        scenario.title = req.title
    if req.description is not None:
        scenario.description = req.description
    if req.steps is not None:
        scenario.steps = req.steps
    
    db.commit()
    db.refresh(scenario)
    return scenario


@router.delete("/{scenario_id}", status_code=204)
def delete_scenario(
    scenario_id: UUID,
    db: Session = Depends(get_db)
):
    """删除场景"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # 检查是否有关联的测试用例
    testcase_count = db.query(TestCase).filter(TestCase.scenario_id == scenario_id).count()
    if testcase_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该场景下存在 {testcase_count} 个关联的测试用例，请先删除测试用例后再删除场景"
        )

    db.delete(scenario)
    db.commit()
    return None


@router.post("/{scenario_id}/approve", response_model=ScenarioResponse)
def approve_scenario(
    scenario_id: UUID,
    reviewer: str,
    comment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """审核场景（批准）"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # 使用审核服务
    approval_service = ApprovalService(db)
    
    # 查找待审核记录
    approvals = approval_service.get_approval_history(
        entity_type="scenario",
        entity_id=scenario_id,
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
    
    db.refresh(scenario)
    return scenario


@router.post("/{scenario_id}/reject", response_model=ScenarioResponse)
def reject_scenario(
    scenario_id: UUID,
    reviewer: str,
    comment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """审核场景（拒绝）"""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # 使用审核服务
    approval_service = ApprovalService(db)
    
    # 查找待审核记录
    approvals = approval_service.get_approval_history(
        entity_type="scenario",
        entity_id=scenario_id,
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
    
    db.refresh(scenario)
    return scenario


@router.post("/batch-approve", response_model=BatchApprovalResponse)
def batch_approve_scenarios(
    req: BatchApprovalRequest,
    db: Session = Depends(get_db)
):
    """
    批量审核场景（批准）
    
    一次性批准多个场景
    """
    if req.entity_type != "scenario":
        raise HTTPException(status_code=400, detail="实体类型必须为 scenario")
    
    approval_service = ApprovalService(db)
    results = approval_service.batch_approve(
        entity_type="scenario",
        entity_ids=req.entity_ids,
        reviewer=req.reviewer,
        comment=req.comment
    )
    
    success_count = sum(1 for r in results if r.get("success"))
    failed_count = len(results) - success_count
    
    return BatchApprovalResponse(
        total=len(results),
        success_count=success_count,
        failed_count=failed_count,
        results=[BatchApprovalResult(**r) for r in results]
    )


@router.post("/batch-reject", response_model=BatchApprovalResponse)
def batch_reject_scenarios(
    req: BatchApprovalRequest,
    db: Session = Depends(get_db)
):
    """
    批量审核场景（拒绝）
    
    一次性拒绝多个场景
    """
    if req.entity_type != "scenario":
        raise HTTPException(status_code=400, detail="实体类型必须为 scenario")
    
    approval_service = ApprovalService(db)
    results = approval_service.batch_reject(
        entity_type="scenario",
        entity_ids=req.entity_ids,
        reviewer=req.reviewer,
        comment=req.comment
    )
    
    success_count = sum(1 for r in results if r.get("success"))
    failed_count = len(results) - success_count
    
    return BatchApprovalResponse(
        total=len(results),
        success_count=success_count,
        failed_count=failed_count,
        results=[BatchApprovalResult(**r) for r in results]
    )
