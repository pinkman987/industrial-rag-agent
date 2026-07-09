from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class StageTwoDatabaseContractTests(unittest.TestCase):
    def test_requirements_only_add_stage_two_database_dependencies(self):
        requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        self.assertIn("SQLAlchemy", requirements)
        self.assertIn("PyMySQL", requirements)

        banned_dependencies = {"mysqlclient", "langgraph", "streamlit"}
        lower_requirements = {item.strip().lower() for item in requirements}
        self.assertTrue(banned_dependencies.isdisjoint(lower_requirements))

    def test_env_example_contains_mysql_defaults(self):
        env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
        expected_lines = [
            "MYSQL_HOST=127.0.0.1",
            "MYSQL_PORT=3306",
            "MYSQL_USER=rag_user",
            "MYSQL_PASSWORD=rag_password",
            "MYSQL_DATABASE=industrial_rag",
        ]

        for line in expected_lines:
            self.assertIn(line, env_example)

    def test_docker_compose_defines_mysql_healthcheck(self):
        compose_file = PROJECT_ROOT / "docker-compose.yml"
        self.assertTrue(compose_file.exists())
        content = compose_file.read_text(encoding="utf-8")

        for expected in [
            "MYSQL_DATABASE: industrial_rag",
            "MYSQL_USER: rag_user",
            "MYSQL_PASSWORD: rag_password",
            '"3306:3306"',
            "healthcheck:",
            "mysqladmin",
        ]:
            self.assertIn(expected, content)

    def test_init_db_script_is_idempotent_by_business_keys(self):
        init_script = PROJECT_ROOT / "scripts" / "init_db.py"
        self.assertTrue(init_script.exists())
        content = init_script.read_text(encoding="utf-8")

        self.assertIn("device_code", content)
        self.assertIn("work_order_no", content)
        self.assertIn("alarm_code", content)
        self.assertNotIn("delete(", content)
        self.assertNotIn("drop_all", content)


if __name__ == "__main__":
    unittest.main()
