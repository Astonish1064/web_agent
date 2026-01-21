import unittest
from unittest.mock import MagicMock
from src.domain import WebsiteSpec, GenerationContext, Task, InstrumentationSpec, PageSpec
from src.interfaces import ISpecGenerator, IBackendGenerator, IFrontendGenerator, IEvaluatorGenerator, IInstrumentationGenerator
# Note: src.pipeline does not exist yet - this is TDD
# We will import it, expecting failure until we create it, 
# or we define the test expecting to implement the class next.

class TestWebGenPipeline(unittest.TestCase):
    def setUp(self):
        # Create Mocks for all dependencies
        self.mock_spec_gen = MagicMock(spec=ISpecGenerator)
        self.mock_backend_gen = MagicMock(spec=IBackendGenerator)
        self.mock_frontend_gen = MagicMock(spec=IFrontendGenerator)
        self.mock_evaluator_gen = MagicMock(spec=IEvaluatorGenerator)
        self.mock_instr_gen = MagicMock(spec=IInstrumentationGenerator) # NEW

        # Setup expected return values
        self.test_spec = WebsiteSpec(
            seed="test_seed", 
            tasks=[Task(id="1", description="test task", complexity=1, required_steps=[])],
            pages=[PageSpec(name="Home", filename="index.html", description="Home")]
        )
        self.mock_spec_gen.generate.return_value = self.test_spec
        self.mock_instr_gen.generate_spec.return_value = InstrumentationSpec() # NEW
        self.mock_backend_gen.generate_logic.return_value = "console.log('logic');"
        self.mock_frontend_gen.generate_page.return_value = "<html></html>"
        self.mock_evaluator_gen.generate_evaluator.return_value = "checkStatus();"

    def test_pipeline_execution_flow(self):
        """
        Verify that the pipeline orchestrates the generators correctly:
        1. SpecGen provides spec
        2. BackendGen uses spec to get logic
        3. FrontendGen uses spec + logic to get HTML
        4. EvaluatorGen uses spec to get evaluator
        """
        # Import inside test to allow file creation step after this file is written
        from src.pipeline import WebGenPipeline 
        
        pipeline = WebGenPipeline(
            spec_gen=self.mock_spec_gen,
            instr_gen=self.mock_instr_gen, # NEW
            backend_gen=self.mock_backend_gen,
            frontend_gen=self.mock_frontend_gen,
            evaluator_gen=self.mock_evaluator_gen
        )

        # Execute
        context = pipeline.run("test_seed", output_dir="/tmp/test_output")

        # Assertions
        # 1. Verify Spec Generation
        self.mock_spec_gen.generate.assert_called_once_with("test_seed")
        self.assertEqual(context.spec, self.test_spec)

        # 2. Verify Backend Generation (called with spec AND instr_spec)
        self.mock_backend_gen.generate_logic.assert_called_once()
        args, _ = self.mock_backend_gen.generate_logic.call_args
        self.assertEqual(args[0], self.test_spec)
        self.assertIsInstance(args[1], InstrumentationSpec)
        
        self.assertEqual(context.backend_code, "console.log('logic');")

        # 3. Verify Frontend Generation
        # It should be called for each page (we have 1)
        self.mock_frontend_gen.generate_page.assert_called_once()
        args, _ = self.mock_frontend_gen.generate_page.call_args
        self.assertEqual(args[0], self.test_spec)
        self.assertIsInstance(args[1], PageSpec) # Passed the page object
        self.assertEqual(args[2], "console.log('logic');") # Passed the logic

        # 4. Verify Evaluator Generation
        self.mock_evaluator_gen.generate_evaluator.assert_called_once_with(self.test_spec)
        self.assertEqual(context.evaluator_code, "checkStatus();")

if __name__ == '__main__':
    unittest.main()
