from datetime import datetime
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class StageThreeToolsContractTests(unittest.TestCase):
    def test_tool_functions_can_be_imported(self):
        from app.tools.rag_tools import search_knowledge_base
        from app.tools.db_tools import query_alarm_records, query_device_info, query_maintenance_records

        self.assertTrue(callable(search_knowledge_base))
        self.assertTrue(callable(query_device_info))
        self.assertTrue(callable(query_alarm_records))
        self.assertTrue(callable(query_maintenance_records))

    def test_rag_tool_returns_dict_with_required_fields(self):
        from app.tools import rag_tools

        raw_results = [
            {
                "content": "SV300伺服电机E-05报警通常与过载有关。",
                "metadata": {"file_name": "SV300_servo_manual.txt", "page": None, "chunk_index": 0},
                "similarity_score": 0.72,
            }
        ]
        settings = SimpleNamespace(top_k=4, similarity_threshold=0.5)

        with patch.object(rag_tools, "get_settings", return_value=settings), patch.object(
            rag_tools, "_search_knowledge_base", return_value=raw_results
        ):
            result = rag_tools.search_knowledge_base("SV300伺服电机E-05报警怎么处理？")

        self.assertIsInstance(result, dict)
        self.assertEqual(result["success"], True)
        self.assertEqual(result["tool_name"], "search_knowledge_base")
        self.assertIn("summary", result)
        self.assertEqual(result["query"], "SV300伺服电机E-05报警怎么处理？")
        self.assertEqual(len(result["sources"]), 1)
        self.assertIn("similarity_score", result["sources"][0])

    def test_rag_tool_returns_empty_sources_without_reliable_evidence(self):
        from app.tools import rag_tools

        settings = SimpleNamespace(top_k=4, similarity_threshold=0.8)
        with patch.object(rag_tools, "get_settings", return_value=settings), patch.object(
            rag_tools, "_search_knowledge_base", return_value=[]
        ):
            result = rag_tools.search_knowledge_base("锅炉水位异常怎么处理？")

        self.assertIsInstance(result, dict)
        self.assertEqual(result["success"], True)
        self.assertEqual(result["tool_name"], "search_knowledge_base")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["summary"], "知识库未检索到高于阈值的可靠依据。")

    def test_db_tools_return_dicts_with_required_fields(self):
        from app.tools import db_tools

        fake_db = _FakeDb()
        fake_device = SimpleNamespace(
            id=1,
            device_code="SV300-01",
            device_name="SV300伺服电机",
            device_type="伺服系统",
            location="一车间A线",
            manufacturer="华东自动化",
            install_date=None,
            status="running",
        )
        fake_alarm = SimpleNamespace(
            alarm_code="E-05",
            alarm_level="high",
            alarm_message="过载报警",
            occurred_at=datetime(2026, 6, 20, 9, 15, 0),
            resolved_at=datetime(2026, 6, 20, 10, 5, 0),
            status="resolved",
        )
        fake_maintenance = SimpleNamespace(
            work_order_no="WO-SV300-001",
            fault_description="SV300伺服电机出现E-05过载报警。",
            root_cause="机械负载偏高。",
            solution="检查负载并调整加减速参数。",
            maintainer="张工",
            started_at=datetime(2026, 6, 20, 9, 30, 0),
            finished_at=datetime(2026, 6, 20, 10, 20, 0),
        )

        with patch.object(db_tools, "SessionLocal", return_value=fake_db), patch.object(
            db_tools.crud, "get_device_by_code", return_value=fake_device
        ), patch.object(db_tools.crud, "list_alarm_records", return_value=[fake_alarm]), patch.object(
            db_tools.crud, "list_maintenance_records", return_value=[fake_maintenance]
        ):
            device_result = db_tools.query_device_info("SV300-01")
            alarm_result = db_tools.query_alarm_records("SV300-01")
            maintenance_result = db_tools.query_maintenance_records("SV300-01")

        for result in [device_result, alarm_result, maintenance_result]:
            self.assertIsInstance(result, dict)
            self.assertEqual(result["success"], True)
            self.assertIn("tool_name", result)
            self.assertIn("summary", result)

        self.assertEqual(device_result["tool_name"], "query_device_info")
        self.assertEqual(alarm_result["tool_name"], "query_alarm_records")
        self.assertEqual(maintenance_result["tool_name"], "query_maintenance_records")
        self.assertEqual(alarm_result["data"][0]["alarm_code"], "E-05")
        self.assertEqual(maintenance_result["data"][0]["work_order_no"], "WO-SV300-001")
        self.assertTrue(fake_db.closed)

    def test_db_tool_handles_missing_device_without_unhandled_exception(self):
        from app.tools import db_tools

        with patch.object(db_tools, "SessionLocal", return_value=_FakeDb()), patch.object(
            db_tools.crud, "get_device_by_code", return_value=None
        ):
            result = db_tools.query_device_info("NOT_EXISTS")

        self.assertIsInstance(result, dict)
        self.assertEqual(result["success"], False)
        self.assertEqual(result["tool_name"], "query_device_info")
        self.assertIn("summary", result)
        self.assertIn("设备不存在", result["summary"])


class _FakeDb:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


if __name__ == "__main__":
    unittest.main()
