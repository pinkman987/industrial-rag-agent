import unittest
from unittest.mock import patch


class StageFourReportContractTests(unittest.TestCase):
    def test_diagnosis_report_schemas_can_be_imported(self):
        from app.schemas.diagnosis import DiagnosisReportRequest, DiagnosisReportResponse

        request = DiagnosisReportRequest(
            question="SV300伺服电机出现E-05报警，请生成一份诊断报告。",
            session_id="report-session-001",
            device_code="SV300-01",
        )
        response = DiagnosisReportResponse(
            message="已生成Markdown诊断报告。",
            report_id="report-session-001-id",
            report_markdown="# 工业设备故障诊断报告",
            evidence={},
            tool_calls=[],
            session_id="report-session-001",
        )

        self.assertEqual(request.device_code, "SV300-01")
        self.assertEqual(response.session_id, "report-session-001")

    def test_report_generator_builds_required_markdown_sections(self):
        from app.diagnosis.report_generator import generate_markdown_report

        diagnosis_result = _sample_diagnosis_result()
        report = generate_markdown_report(
            question="SV300伺服电机出现E-05报警，请生成一份诊断报告。",
            device_code="SV300-01",
            diagnosis_result=diagnosis_result,
        )

        for expected in [
            "工业设备故障诊断报告",
            "基本信息",
            "故障现象",
            "设备基础信息",
            "知识库依据",
            "历史报警依据",
            "历史维修依据",
            "综合诊断结论",
            "工具调用记录",
            "结论说明",
        ]:
            self.assertIn(expected, report)

    def test_report_generator_handles_missing_device_code_and_empty_evidence(self):
        from app.diagnosis.report_generator import generate_markdown_report

        diagnosis_result = {
            "diagnosis": "缺少设备编号，无法结合设备台账、历史报警和维修记录分析。",
            "evidence": {
                "knowledge_sources": [],
                "device_info": None,
                "alarm_records": [],
                "maintenance_records": [],
            },
            "tool_calls": [],
            "session_id": "report-session-003",
        }
        report = generate_markdown_report(
            question="锅炉水位异常，请生成一份诊断报告。",
            device_code=None,
            diagnosis_result=diagnosis_result,
        )

        self.assertIn("未提供设备编号，无法结合设备台账、历史报警和维修记录分析。", report)
        self.assertIn("知识库未检索到高于阈值的可靠依据。", report)
        self.assertIn("未查询到历史报警记录。", report)
        self.assertIn("未查询到历史维修记录。", report)

    def test_diagnosis_report_route_is_registered_and_reuses_analyze_fault(self):
        diagnosis_api = _read_file("app/api/diagnosis.py")

        self.assertIn('@router.post("/report"', diagnosis_api)
        self.assertIn("generate_markdown_report", diagnosis_api)
        self.assertIn("analyze_fault", diagnosis_api)

    def test_report_api_returns_required_structure_with_mocked_diagnosis(self):
        from app.api import diagnosis as diagnosis_api
        from app.schemas.diagnosis import DiagnosisReportRequest

        with patch.object(diagnosis_api, "analyze_fault", return_value=_sample_diagnosis_result()):
            response = diagnosis_api.generate_diagnosis_report_api(
                DiagnosisReportRequest(
                    question="SV300伺服电机出现E-05报警，请生成一份诊断报告。",
                    session_id="report-session-001",
                    device_code="SV300-01",
                )
            )

        self.assertEqual(response.message, "已生成Markdown诊断报告。")
        self.assertTrue(response.report_id)
        self.assertEqual(response.session_id, "report-session-001")
        self.assertIn("工业设备故障诊断报告", response.report_markdown)
        self.assertIn("query_device_info", response.report_markdown)


def _sample_diagnosis_result() -> dict:
    return {
        "message": "已完成故障诊断流程编排。",
        "diagnosis": (
            "## 故障现象\nSV300伺服电机出现E-05报警。\n"
            "## 知识库依据\nE-05与过载有关。\n"
            "## 历史报警依据\n近期有E-05报警。\n"
            "## 历史维修依据\n历史维修显示机械负载偏高。\n"
            "## 可能原因\n机械负载过高。\n"
            "## 排查步骤\n检查负载和参数。\n"
            "## 维修建议\n清理导轨并调整加减速参数。\n"
            "## 注意事项\n维修前确认安全。"
        ),
        "evidence": {
            "knowledge_sources": [
                {
                    "file_name": "SV300_servo_manual.txt",
                    "page": None,
                    "chunk_index": 0,
                    "similarity_score": 0.82,
                    "content_preview": "E-05报警与伺服过载有关。",
                }
            ],
            "device_info": {
                "device_code": "SV300-01",
                "device_name": "SV300伺服电机",
                "device_type": "伺服系统",
                "location": "一车间A线",
                "manufacturer": "华东自动化",
                "status": "running",
            },
            "alarm_records": [
                {
                    "alarm_code": "E-05",
                    "alarm_level": "major",
                    "alarm_message": "伺服驱动器过载报警",
                    "occurred_at": "2026-06-20T09:15:00",
                    "status": "resolved",
                }
            ],
            "maintenance_records": [
                {
                    "work_order_no": "WO-SV300-001",
                    "fault_description": "SV300伺服电机运行中出现E-05过载报警。",
                    "root_cause": "导轨润滑不足，机械负载偏高。",
                    "solution": "清理导轨并调整加减速时间。",
                    "maintainer": "张工",
                    "started_at": "2026-06-20T09:30:00",
                    "finished_at": "2026-06-20T10:20:00",
                }
            ],
        },
        "tool_calls": [
            {
                "tool_name": "query_device_info",
                "arguments": {"device_code": "SV300-01"},
                "success": True,
                "summary": "已查询到设备基础信息。",
                "result_preview": "SV300伺服电机",
            }
        ],
        "session_id": "report-session-001",
    }


def _read_file(path: str) -> str:
    from pathlib import Path

    return Path(path).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
