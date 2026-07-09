from pathlib import Path
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StageThreeToolCallsHistoryContractTests(unittest.TestCase):
    def test_chat_record_model_and_init_script_support_tool_calls_json(self):
        model_content = (PROJECT_ROOT / "app" / "db" / "models.py").read_text(encoding="utf-8")
        init_content = (PROJECT_ROOT / "scripts" / "init_db.py").read_text(encoding="utf-8")

        self.assertIn("tool_calls_json", model_content)
        self.assertIn("tool_calls_json", init_content)
        self.assertIn("ensure_chat_records_tool_calls_column", init_content)
        self.assertIn("ALTER TABLE chat_records ADD COLUMN tool_calls_json", init_content)

    def test_save_chat_record_persists_tool_calls_json(self):
        from app.db.base import Base
        from app.db import crud

        engine = create_engine("sqlite:///:memory:")
        TestingSessionLocal = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            tool_calls = [
                {
                    "tool_name": "query_alarm_records",
                    "arguments": {"device_code": "SV300-01", "limit": 5},
                    "success": True,
                    "summary": "已查询到设备近期报警记录。",
                    "result_preview": "E-05过载报警",
                }
            ]

            record = crud.save_chat_record(
                db,
                session_id="tool-history-001",
                question="SV300伺服电机出现E-05报警，结合历史报警和维修记录应该怎么排查？",
                answer="结合历史报警和维修记录排查。",
                sources=[],
                tool_calls=tool_calls,
                device_id=None,
            )

            self.assertIn("query_alarm_records", record.tool_calls_json)
            self.assertIn("tool-history-001", record.session_id)
        finally:
            db.close()

    def test_history_response_includes_tool_calls(self):
        schema_content = (PROJECT_ROOT / "app" / "schemas" / "rag.py").read_text(encoding="utf-8")
        chat_content = (PROJECT_ROOT / "app" / "api" / "chat.py").read_text(encoding="utf-8")

        self.assertIn("tool_calls", schema_content)
        self.assertIn("_decode_tool_calls", chat_content)
        self.assertIn("tool_calls=_decode_tool_calls", chat_content)

    def test_ask_with_tools_route_saves_tool_calls_without_replacing_original_chat_route(self):
        tool_chat_api = (PROJECT_ROOT / "app" / "api" / "tool_chat.py").read_text(encoding="utf-8")
        original_chat_api = (PROJECT_ROOT / "app" / "api" / "chat.py").read_text(encoding="utf-8")

        self.assertIn("save_chat_record", tool_chat_api)
        self.assertIn("tool_calls=result[\"tool_calls\"]", tool_chat_api)
        self.assertIn("get_device_by_code", tool_chat_api)
        self.assertIn('@router.post("/ask"', original_chat_api)


if __name__ == "__main__":
    unittest.main()
