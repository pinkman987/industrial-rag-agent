from pathlib import Path
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StageFourReportHistoryContractTests(unittest.TestCase):
    def test_diagnosis_report_model_can_be_imported(self):
        from app.db.models import DiagnosisReport

        self.assertEqual(DiagnosisReport.__tablename__, "diagnosis_reports")

    def test_report_history_crud_functions_can_be_imported(self):
        from app.db import crud

        self.assertTrue(callable(crud.save_diagnosis_report))
        self.assertTrue(callable(crud.get_diagnosis_report_by_report_id))
        self.assertTrue(callable(crud.get_diagnosis_reports_by_session_id))

    def test_diagnosis_report_response_contains_report_id(self):
        from app.schemas.diagnosis import DiagnosisReportResponse

        response = DiagnosisReportResponse(
            message="已生成Markdown诊断报告。",
            report_id="report-001",
            report_markdown="# 工业设备故障诊断报告",
            evidence={},
            tool_calls=[],
            session_id="report-history-001",
        )

        self.assertEqual(response.report_id, "report-001")

    def test_report_history_routes_are_registered(self):
        diagnosis_api = (PROJECT_ROOT / "app" / "api" / "diagnosis.py").read_text(encoding="utf-8")

        self.assertIn('@router.get("/reports/{report_id}"', diagnosis_api)
        self.assertIn('@router.get("/reports/session/{session_id}"', diagnosis_api)
        self.assertIn("get_diagnosis_report_by_report_id", diagnosis_api)
        self.assertIn("get_diagnosis_reports_by_session_id", diagnosis_api)

    def test_crud_saves_and_queries_diagnosis_reports_as_dicts(self):
        from app.db.base import Base
        from app.db import crud

        engine = create_engine("sqlite:///:memory:")
        TestingSessionLocal = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            saved = crud.save_diagnosis_report(
                db,
                report_id="report-history-contract-001",
                session_id="report-history-001",
                device_id=None,
                question="SV300伺服电机出现E-05报警，请生成一份诊断报告。",
                report_markdown="# 工业设备故障诊断报告",
                evidence={"knowledge_sources": []},
                tool_calls=[
                    {
                        "tool_name": "search_knowledge_base",
                        "arguments": {"query": "E-05"},
                        "success": True,
                        "summary": "知识库未检索到高于阈值的可靠依据。",
                    }
                ],
            )

            by_report_id = crud.get_diagnosis_report_by_report_id(db, "report-history-contract-001")
            by_session_id = crud.get_diagnosis_reports_by_session_id(db, "report-history-001")

            self.assertIsInstance(saved, dict)
            self.assertEqual(saved["report_id"], "report-history-contract-001")
            self.assertEqual(by_report_id["evidence"], {"knowledge_sources": []})
            self.assertEqual(by_report_id["tool_calls"][0]["tool_name"], "search_knowledge_base")
            self.assertEqual(len(by_session_id), 1)
            self.assertEqual(by_session_id[0]["question"], "SV300伺服电机出现E-05报警，请生成一份诊断报告。")
        finally:
            db.close()

    def test_report_api_saves_report_when_db_session_is_provided(self):
        from app.api import diagnosis as diagnosis_api
        from app.db.base import Base
        from app.db import crud
        from app.schemas.diagnosis import DiagnosisReportRequest

        engine = create_engine("sqlite:///:memory:")
        TestingSessionLocal = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            diagnosis_result = {
                "message": "已完成故障诊断流程编排。",
                "diagnosis": "## 可能原因\n机械负载过高。",
                "evidence": {
                    "knowledge_sources": [],
                    "device_info": None,
                    "alarm_records": [],
                    "maintenance_records": [],
                },
                "tool_calls": [
                    {
                        "tool_name": "search_knowledge_base",
                        "arguments": {"query": "E-05"},
                        "success": True,
                        "summary": "知识库未检索到高于阈值的可靠依据。",
                    }
                ],
                "session_id": "report-history-api-001",
            }

            with patch.object(diagnosis_api, "analyze_fault", return_value=diagnosis_result):
                response = diagnosis_api.generate_diagnosis_report_api(
                    DiagnosisReportRequest(
                        question="SV300伺服电机出现E-05报警，请生成一份诊断报告。",
                        session_id="report-history-api-001",
                        device_code="SV300-01",
                    ),
                    db=db,
                )

            saved = crud.get_diagnosis_report_by_report_id(db, response.report_id)
            self.assertIsNotNone(saved)
            self.assertEqual(saved["session_id"], "report-history-api-001")
            self.assertIn("工业设备故障诊断报告", saved["report_markdown"])
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
