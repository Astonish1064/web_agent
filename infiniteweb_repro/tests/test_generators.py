import unittest
from src.mocks import MockBackendGenerator
from src.domain import WebsiteSpec

class TestMockGenerators(unittest.TestCase):
    def test_backend_trajectory_logging(self):
        generator = MockBackendGenerator()
        spec = WebsiteSpec(seed="test", tasks=[], data_models=[], interfaces=[])
        
        logic_code = generator.generate_logic(spec)
        
        self.assertIn("trajectory_log", logic_code)
        self.assertIn("function logTraj", logic_code)
        self.assertIn("logTraj('FUNCTION_CALL'", logic_code)

if __name__ == '__main__':
    unittest.main()
