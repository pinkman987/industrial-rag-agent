from pathlib import Path
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StageTwoChatHistoryContractTests(unittest.TestCase):
    def test_rag_schemas_support_session_and_history_fields(self):
        schema_content = (PROJECT_ROOT / "app" / "schemas" / "rag.py").read_text(encoding="utf-8")

        self.assertIn("session_id", schema_content)
        self.assertIn("device_code", schema_content)
        self.assertIn("class ChatHistoryItem", schema_content)
        self.assertIn("class ChatHistoryResponse", schema_content)
        self.assertIn("sources: list[Source]", schema_content)

    def test_chat_router_saves_records_and_exposes_history_route(self):
        chat_content = (PROJECT_ROOT / "app" / "api" / "chat.py").read_text(encoding="utf-8")

        self.assertIn("answer_question(payload.question)", chat_content)
        self.assertIn("save_chat_record", chat_content)
        self.assertIn("list_chat_history_by_session", chat_content)
        self.assertIn('"/history/{session_id}"', chat_content)
        self.assertIn("uuid4", chat_content)

    def test_crud_contains_chat_history_functions(self):
        crud_content = (PROJECT_ROOT / "app" / "db" / "crud.py").read_text(encoding="utf-8")

        self.assertIn("def save_chat_record", crud_content)
        self.assertIn("def list_chat_history_by_session", crud_content)
        self.assertIn("ChatRecord", crud_content)
        self.assertIn("sources_json", crud_content)

    def test_previous_devices_contract_allows_chat_persistence_after_third_batch(self):
        devices_test_content = (
            PROJECT_ROOT / "tests" / "test_stage_two_devices_api_contract.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("self.assertNotIn(\"save_chat\"", devices_test_content)
        self.assertNotIn("self.assertNotIn(\"ChatRecord\"", devices_test_content)

    def test_crud_saves_and_lists_chat_records_by_session(self):
        from app.db.base import Base
        from app.db import crud

        engine = create_engine("sqlite:///:memory:")
        TestingSessionLocal = sessionmaker(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            sources = [
                {
                    "file_name": "SV300_servo_manual.txt",
                    "page": None,
                    "chunk_index": 1,
                    "similarity_score": 0.91,
                    "content_preview": "E-05报警表示编码器反馈异常",
                }
            ]

            crud.save_chat_record(
                db,
                session_id="test-session-001",
                question="SV300伺服电机出现E-05报警应该怎么排查？",
                answer="检查编码器线缆。",
                sources=sources,
                device_id=None,
            )

            records = crud.list_chat_history_by_session(db, "test-session-001")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].session_id, "test-session-001")
            self.assertEqual(records[0].sources_json, __import__("json").dumps(sources, ensure_ascii=False))
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
