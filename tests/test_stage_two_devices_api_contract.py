from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StageTwoDevicesApiContractTests(unittest.TestCase):
    def test_devices_schema_and_router_files_exist(self):
        self.assertTrue((PROJECT_ROOT / "app" / "schemas" / "db.py").exists())
        self.assertTrue((PROJECT_ROOT / "app" / "api" / "devices.py").exists())

    def test_main_registers_devices_router_without_changing_chat_flow(self):
        main_content = (PROJECT_ROOT / "app" / "main.py").read_text(encoding="utf-8")
        chat_content = (PROJECT_ROOT / "app" / "api" / "chat.py").read_text(encoding="utf-8")

        self.assertIn("devices", main_content)
        self.assertIn("app.include_router(devices.router)", main_content)
        self.assertIn("answer_question(payload.question)", chat_content)

    def test_crud_contains_device_query_functions(self):
        crud_content = (PROJECT_ROOT / "app" / "db" / "crud.py").read_text(encoding="utf-8")

        for function_name in [
            "list_devices",
            "get_device_by_code",
            "list_alarm_records",
            "list_maintenance_records",
        ]:
            self.assertIn(f"def {function_name}", crud_content)

    def test_devices_router_exposes_required_paths(self):
        router_content = (PROJECT_ROOT / "app" / "api" / "devices.py").read_text(encoding="utf-8")

        self.assertGreaterEqual(router_content.count("@router.get("), 4)
        for route_fragment in [
            '""',
            '"/{device_code}"',
            '"/{device_code}/alarms"',
            '"/{device_code}/maintenance"',
        ]:
            self.assertIn(route_fragment, router_content)
        self.assertIn("Query(5", router_content)


if __name__ == "__main__":
    unittest.main()
