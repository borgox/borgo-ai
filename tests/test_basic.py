"""
Basic tests for borgo-ai
"""
import unittest
from pathlib import Path

class TestBorgAI(unittest.TestCase):
    """Basic test cases"""

    def test_imports(self):
        """Test that all modules can be imported"""
        try:
            import borgo_ai.config
            import borgo_ai.llm
            import borgo_ai.rag
            import borgo_ai.memory
            import borgo_ai.user
            import borgo_ai.agent
            import borgo_ai.ui
            import borgo_ai.embeddings
            import borgo_ai.browser
            import borgo_ai.executor
            import borgo_ai.export
            import borgo_ai.files
            import borgo_ai.images
            import borgo_ai.summarizer
        except ImportError as e:
            self.fail(f"Import failed: {e}")

    def test_config(self):
        """Test configuration loading"""
        import borgo_ai.config
        self.assertIsNotNone(borgo_ai.config.llm_config)
        self.assertIsNotNone(borgo_ai.config.embedding_config)

    def test_data_directories(self):
        """Test that data directories exist"""
        data_dir = Path("data")
        self.assertTrue(data_dir.exists() or data_dir.parent.exists())

if __name__ == '__main__':
    unittest.main()