import unittest
from unittest.mock import patch


class StageFourDiagnosisContractTests(unittest.TestCase):
    def test_diagnosis_schemas_can_be_imported(self):
        from app.schemas.diagnosis import DiagnosisRequest, DiagnosisResponse

        request = DiagnosisRequest(
            question="SV300伺服电机出现E-05报警，现场应该如何排查？",
            session_id="diagnosis-session-001",
            device_code="SV300-01",
        )
        response = DiagnosisResponse(
            message="ok",
            diagnosis="diagnosis",
            evidence={},
            tool_calls=[],
            session_id="diagnosis-session-001",
        )

        self.assertEqual(request.device_code, "SV300-01")
        self.assertEqual(response.session_id, "diagnosis-session-001")

    def test_fault_diagnosis_module_returns_required_structure_with_mocks(self):
        from app.diagnosis import fault_diagnosis

        def fake_execute(tool_name, arguments):
            fake_results = {
                "query_device_info": {"data": {"device_code": "SV300-01", "device_name": "SV300伺服电机"}},
                "search_knowledge_base": {
                    "sources": [
                        {
                            "file_name": "SV300_servo_manual.txt",
                            "page": None,
                            "chunk_index": 0,
                            "similarity_score": 0.8,
                            "content_preview": "E-05报警与过载有关。",
                        }
                    ]
                },
                "query_alarm_records": {"data": [{"alarm_code": "E-05"}]},
                "query_maintenance_records": {"data": [{"work_order_no": "WO-SV300-001"}]},
            }
            result = {
                "success": True,
                "tool_name": tool_name,
                "arguments": arguments,
                "summary": f"{tool_name} ok",
                "result_preview": f"{tool_name} preview",
                "result": fake_results.get(tool_name, {}),
            }
            result["result"].setdefault("success", True)
            result["result"].setdefault("summary", result["summary"])
            return result

        with patch.object(fault_diagnosis, "execute_tool_call", side_effect=fake_execute), patch.object(
            fault_diagnosis,
            "_generate_diagnosis",
            return_value="## 故障现象\n...\n## 知识库依据\n...\n## 历史报警依据\n...\n## 历史维修依据\n...\n## 可能原因\n...\n## 排查步骤\n...\n## 维修建议\n...\n## 注意事项\n...",
        ):
            result = fault_diagnosis.analyze_fault(
                question="SV300伺服电机出现E-05报警，现场应该如何排查？",
                session_id="diagnosis-session-001",
                device_code="SV300-01",
            )

        self.assertEqual(result["session_id"], "diagnosis-session-001")
        self.assertIn("message", result)
        self.assertIn("diagnosis", result)
        self.assertIn("evidence", result)
        self.assertIn("tool_calls", result)
        self.assertEqual(
            [call["tool_name"] for call in result["tool_calls"]],
            [
                "query_device_info",
                "search_knowledge_base",
                "query_alarm_records",
                "query_maintenance_records",
            ],
        )
        self.assertIn("knowledge_sources", result["evidence"])
        self.assertIn("device_info", result["evidence"])
        self.assertIn("alarm_records", result["evidence"])
        self.assertIn("maintenance_records", result["evidence"])

    def test_fault_diagnosis_without_device_code_skips_business_data_tools(self):
        from app.diagnosis import fault_diagnosis

        with patch.object(fault_diagnosis, "execute_tool_call") as execute_mock:
            execute_mock.return_value = {
                "success": True,
                "tool_name": "search_knowledge_base",
                "arguments": {"query": "锅炉水位异常应该怎么处理？", "device_code": None},
                "summary": "知识库未检索到高于阈值的可靠依据。",
                "result_preview": "[]",
                "result": {"success": True, "sources": [], "summary": "知识库未检索到高于阈值的可靠依据。"},
            }
            result = fault_diagnosis.analyze_fault(
                question="锅炉水位异常应该怎么处理？",
                session_id="diagnosis-session-003",
            )

        self.assertEqual([call["tool_name"] for call in result["tool_calls"]], ["search_knowledge_base"])
        self.assertEqual(result["evidence"]["device_info"], None)
        self.assertEqual(result["evidence"]["alarm_records"], [])
        self.assertEqual(result["evidence"]["maintenance_records"], [])
        self.assertIn("缺少设备编号", result["diagnosis"])

    def test_diagnosis_route_is_registered_without_replacing_existing_routes(self):
        main_content = _read_file("app/main.py")
        diagnosis_api = _read_file("app/api/diagnosis.py")
        chat_api = _read_file("app/api/chat.py")
        tool_chat_api = _read_file("app/api/tool_chat.py")

        self.assertIn("diagnosis", main_content)
        self.assertIn("app.include_router(diagnosis.router)", main_content)
        self.assertIn('@router.post("/analyze"', diagnosis_api)
        self.assertIn('@router.post("/ask"', chat_api)
        self.assertIn('@router.post("/ask-with-tools"', tool_chat_api)


def _read_file(path: str) -> str:
    from pathlib import Path

    return Path(path).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
