import unittest
from src.mocks import MockBackendGenerator
from src.domain import WebsiteSpec, InstrumentationSpec, VariableRequirement

class TestInstrumentationRefactor(unittest.TestCase):
    def test_dynamic_instrumentation_injection(self):
        """
        Verify that BackendGenerator dynamically injects code based on InstrumentationSpec.
        """
        generator = MockBackendGenerator()
        spec = WebsiteSpec(seed="test", tasks=[], data_models=[], interfaces=[])
        
        # Create a custom instrumentation requirement
        instr_spec = InstrumentationSpec(requirements=[
            VariableRequirement(
                variable_name="test_checkout_flag",
                set_in_function="addToCart",
                set_condition="always"
            )
        ])
        
        # Generate logic with this spec
        logic_code = generator.generate_logic(spec, instr_spec)
        
        # Assertions
        # 1. Base logTraj should still be there (if we keep it as default) or replaced by this system.
        #    For this refactor, we assume logTraj is a standard utility, but 'variable_name' is the custom part.
        self.assertIn("function logTraj", logic_code)
        
        # 2. The CUSTOM variable must be set in local storage
        expected_code = "localStorage.setItem('test_checkout_flag', JSON.stringify(true));"
        self.assertIn(expected_code, logic_code, "Backend should inject code for 'test_checkout_flag'")

if __name__ == '__main__':
    unittest.main()
