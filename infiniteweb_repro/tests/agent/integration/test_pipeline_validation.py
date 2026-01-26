import pytest
import os
import shutil
import tempfile
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.async_pipeline import AsyncWebGenPipeline, GenerationContext
from src.interfaces import ITaskGenerator, IInterfaceDesigner, IArchitectDesigner, IDataGenerator, IBackendGenerator, IFrontendGenerator, IPageDesigner, IEvaluatorGenerator, IInstrumentationGenerator

@pytest.fixture
def mock_generators():
    return {
        "task_gen": MagicMock(ITaskGenerator),
        "interface_designer": MagicMock(IInterfaceDesigner),
        "arch_designer": MagicMock(IArchitectDesigner),
        "data": MagicMock(IDataGenerator),
        "backend": MagicMock(IBackendGenerator),
        "frontend": MagicMock(IFrontendGenerator),
        "designer": MagicMock(IPageDesigner),
        "evaluator": MagicMock(IEvaluatorGenerator),
        "instr": MagicMock(IInstrumentationGenerator)
    }

@pytest.mark.asyncio
async def test_pipeline_regeneration_loop(mock_generators):
    # Setup mocks
    pipeline = AsyncWebGenPipeline(
        task_gen=mock_generators["task_gen"],
        interface_designer=mock_generators["interface_designer"],
        arch_designer=mock_generators["arch_designer"],
        data_gen=mock_generators["data"],
        backend_gen=mock_generators["backend"],
        page_designer=mock_generators["designer"],
        frontend_gen=mock_generators["frontend"],
        instr_gen=mock_generators["instr"],
        evaluator_gen=mock_generators["evaluator"]
    )
    
    # Mock planning phase
    mock_generators["task_gen"].generate = MagicMock(return_value=[])
    mock_generators["interface_designer"].design = MagicMock(return_value=[])
    mock_generators["interface_designer"].wrap = MagicMock(return_value=MagicMock())
    mock_generators["arch_designer"].design = MagicMock(return_value=MagicMock(pages=[]))
    
    # 1. First attempt fails backend test
    # 2. Second attempt passes
    mock_generators["backend"].generate_logic = MagicMock(side_effect=[
        "faulty_code", "healthy_code"
    ])
    mock_generators["backend"].generate_tests = MagicMock(return_value="test_code")
    
    # Mock other steps to just return something
    mock_generators["data"].generate = MagicMock(return_value={})
    mock_generators["instr"].analyze = MagicMock(return_value=[])
    mock_generators["instr"].inject = MagicMock(side_effect=lambda code, reqs: code)
    mock_generators["evaluator"].generate = MagicMock(return_value="eval_code")
    mock_generators["frontend"].generate_framework = MagicMock(return_value="framework")
    mock_generators["designer"].design_functionality = MagicMock(return_value=MagicMock())
    mock_generators["designer"].design_layout = MagicMock(return_value=MagicMock())
    mock_generators["frontend"].generate_html = MagicMock(return_value="<html></html>")
    mock_generators["frontend"].generate_css = MagicMock(return_value="")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Patch EnvironmentHealthChecker to simulate failure then success
        with patch("src.async_pipeline.EnvironmentHealthChecker") as MockChecker:
            checker_inst = MockChecker.return_value
            checker_inst.validate_backend = AsyncMock(side_effect=[
                (False, "Assertion Failed"), # 1st call fails
                (True, None)                 # 2nd call passes
            ])
            checker_inst.validate_frontend = AsyncMock(return_value=(True, None))

            await pipeline.run("test_seed", tmp_dir)
            
            # Assertions
            # Should have called generate_logic twice
            assert mock_generators["backend"].generate_logic.call_count == 2
            # Should have called validate_backend twice
            assert checker_inst.validate_backend.call_count == 2
            
            # Check files written
            assert os.path.exists(os.path.join(tmp_dir, "logic.js"))
            with open(os.path.join(tmp_dir, "logic.js")) as f:
                assert f.read() == "healthy_code"
