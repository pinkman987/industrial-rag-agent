from pathlib import Path
import unittest


class SimilarityScoreTests(unittest.TestCase):
    def test_distance_is_converted_to_similarity_score(self):
        from app.rag.vector_store import distance_to_similarity_score

        self.assertEqual(distance_to_similarity_score(0), 1.0)
        self.assertAlmostEqual(distance_to_similarity_score(1), 0.5)
        self.assertAlmostEqual(distance_to_similarity_score(3), 0.25)


class EvidenceThresholdTests(unittest.TestCase):
    def test_low_similarity_returns_no_sources_and_fixed_prefix(self):
        from app.rag.qa import NO_EVIDENCE_PREFIX, build_no_evidence_answer, filter_reliable_results

        results = [
            {
                "content": "这是一段不够相关的检索结果",
                "metadata": {"file_name": "unknown.txt", "page": None, "chunk_index": 0},
                "similarity_score": 0.2,
            }
        ]

        reliable = filter_reliable_results(results, threshold=0.6)
        answer = build_no_evidence_answer("锅炉水位异常如何处理？")

        self.assertEqual(reliable, [])
        self.assertTrue(answer.startswith(NO_EVIDENCE_PREFIX))


class ModelConfigTests(unittest.TestCase):
    def test_chat_and_embedding_config_are_separate(self):
        from app.core.llm import build_chat_kwargs, build_embedding_kwargs

        class Settings:
            chat_api_key = "deepseek-chat-key"
            chat_base_url = "https://api.deepseek.com"
            chat_model = "deepseek-v4-flash"
            embedding_api_key = "zhipu-embedding-key"
            embedding_base_url = "https://open.bigmodel.cn/api/paas/v4"
            embedding_model = "embedding-3"

        settings = Settings()

        chat_kwargs = build_chat_kwargs(settings)
        embedding_kwargs = build_embedding_kwargs(settings)

        self.assertEqual(chat_kwargs["model"], "deepseek-v4-flash")
        self.assertEqual(chat_kwargs["api_key"], "deepseek-chat-key")
        self.assertEqual(chat_kwargs["base_url"], "https://api.deepseek.com")
        self.assertEqual(embedding_kwargs["model"], "embedding-3")
        self.assertEqual(embedding_kwargs["api_key"], "zhipu-embedding-key")
        self.assertEqual(embedding_kwargs["base_url"], "https://open.bigmodel.cn/api/paas/v4")


class SampleDocumentTests(unittest.TestCase):
    def test_sample_documents_are_present_and_searchable(self):
        sample_dir = Path("data/sample_docs")
        expected_files = [
            "SV300_servo_manual.txt",
            "SV300_servo_maintenance.txt",
            "CONV_A1_sop.txt",
            "CNC_X200_fault_cases.txt",
        ]

        for file_name in expected_files:
            path = sample_dir / file_name
            self.assertTrue(path.exists(), f"{file_name} should exist")
            content = path.read_text(encoding="utf-8")
            for keyword in ["设备名称", "报警码", "故障原因", "排查步骤", "维修建议"]:
                self.assertIn(keyword, content, f"{file_name} should contain {keyword}")


if __name__ == "__main__":
    unittest.main()
