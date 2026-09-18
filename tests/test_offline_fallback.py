import unittest


class OfflineFallbackTests(unittest.TestCase):
    def test_local_search_finds_servo_alarm_document(self):
        from app.rag.local_search import search_sample_documents_locally

        results = search_sample_documents_locally(
            "SV300伺服电机出现E-05报警应该怎么排查？",
            top_k=4,
        )

        self.assertTrue(results)
        self.assertEqual(results[0]["retrieval_mode"], "local_keyword")
        self.assertIn("SV300", results[0]["content"])

    def test_local_results_use_the_offline_threshold(self):
        from app.rag.qa import filter_reliable_results

        results = [
            {
                "content": "本地样例",
                "metadata": {},
                "similarity_score": 0.2,
                "retrieval_mode": "local_keyword",
            }
        ]

        self.assertEqual(len(filter_reliable_results(results, threshold=0.52)), 1)


if __name__ == "__main__":
    unittest.main()
