import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from sqlalchemy.orm import Session
from qualityfoundry.database.models import Execution, TestCase as DBTestCase, ExecutionStatus, Requirement, Scenario as DBScenario
from qualityfoundry.services.observer_service import ObserverService

@pytest.fixture
def db_session():
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.mark.asyncio
async def test_analyze_execution_failure_success(db_session: Session):
    # 1. Setup mock data
    testcase = DBTestCase(
        id=uuid4(),
        title="Test Case for Diagnosis",
        steps=[{"step": "Step 1", "expected": "Success"}],
        scenario_id=uuid4()
    )
    db_session.add(testcase)
    
    execution = Execution(
        id=uuid4(),
        testcase_id=testcase.id,
        environment_id=uuid4(),
        status=ExecutionStatus.FAILED,
        error_message="Connection timeout",
        evidence=[]
    )
    db_session.add(execution)
    db_session.commit()

    # 2. Mock AIService.call_ai
    with patch("qualityfoundry.services.ai_service.AIService.call_ai", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "AI analysis: Network failure detected."
        
        # 3. Call the service
        result = await ObserverService.analyze_execution_failure(db_session, execution.id)
        
        # 4. Assertions
        assert result["status"] == "success"
        assert "ai_analysis" in result
        assert result["ai_analysis"] == "AI analysis: Network failure detected."
        
        # Verify database update
        db_session.refresh(execution)
        assert execution.result["ai_analysis"] == "AI analysis: Network failure detected."

@pytest.mark.asyncio
async def test_analyze_execution_failure_not_found(db_session: Session):
    from qualityfoundry.services.observer_service import ObserverError
    with pytest.raises(ObserverError) as excinfo:
        await ObserverService.analyze_execution_failure(db_session, uuid4())
    assert "Execution not found" in str(excinfo.value)

@pytest.mark.asyncio
async def test_analyze_consistency_success(db_session: Session):
    # Setup req, scenario, testcase
    from qualityfoundry.database.models import Requirement, Scenario
    req = Requirement(id=uuid4(), title="Req 1", content="Content 1")
    db_session.add(req)
    scenario = DBTestCase(id=uuid4(), scenario_id=uuid4()) # Wait, wrong model for scenario
    # Correcting: Scenario use Scenario model
    from qualityfoundry.database.models import Scenario as DBScenario
    sc = DBScenario(id=uuid4(), requirement_id=req.id, title="Sc 1", steps=["step1"])
    db_session.add(sc)
    tc = DBTestCase(id=uuid4(), scenario_id=sc.id, title="TC 1", steps=[{"step": "s1", "expected": "e1"}])
    db_session.add(tc)
    db_session.commit()

    with patch("qualityfoundry.services.ai_service.AIService.call_ai", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "Consistency check passed."
        
        result = await ObserverService.analyze_consistency(db_session, req.id)
        
        assert result["status"] == "success"
        assert "analysis" in result
        assert result["analysis"] == "Consistency check passed."

@pytest.mark.asyncio
async def test_evaluate_coverage_success(db_session: Session):
    from qualityfoundry.database.models import Requirement, Scenario as DBScenario
    req = Requirement(id=uuid4(), title="Req 1", content="Content 1")
    db_session.add(req)
    sc = DBScenario(id=uuid4(), requirement_id=req.id, title="Sc 1", steps=["step1"])
    db_session.add(sc)
    db_session.commit()

    with patch("qualityfoundry.services.ai_service.AIService.call_ai", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "Coverage is 100%."
        
        result = await ObserverService.evaluate_coverage(db_session, req.id)
        
        assert result["status"] == "success"
        assert "coverage_analysis" in result
        assert result["coverage_analysis"] == "Coverage is 100%."
        
@pytest.mark.asyncio
async def test_analyze_consistency_not_found(db_session: Session):
    from qualityfoundry.services.observer_service import ObserverError
    with pytest.raises(ObserverError) as excinfo:
        await ObserverService.analyze_consistency(db_session, uuid4())
    assert "Requirement not found" in str(excinfo.value)

@pytest.mark.asyncio
async def test_evaluate_coverage_not_found(db_session: Session):
    from qualityfoundry.services.observer_service import ObserverError
    with pytest.raises(ObserverError) as excinfo:
        await ObserverService.evaluate_coverage(db_session, uuid4())
    assert "Requirement not found" in str(excinfo.value)

@pytest.mark.asyncio
async def test_get_god_suggestions_not_found(db_session: Session):
    from qualityfoundry.services.observer_service import ObserverError
    with pytest.raises(ObserverError) as excinfo:
        await ObserverService.get_god_suggestions(db_session, uuid4())
    assert "Requirement not found" in str(excinfo.value)
