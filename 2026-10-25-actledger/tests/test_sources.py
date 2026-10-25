import os
import shutil
import sqlite3
import tempfile
import unittest

from actledger.sources import SourceError, records_from_kanban


def build_db(path, runs):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY, assignee TEXT, title TEXT, body TEXT, model_override TEXT
        );
        CREATE TABLE task_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, profile TEXT, status TEXT,
            outcome TEXT, started_at INTEGER, ended_at INTEGER
        );
        """
    )
    connection.execute(
        "INSERT INTO tasks VALUES ('t_1', 'forge', 'Build a thing', 'go build it', 'model-a')"
    )
    connection.execute("INSERT INTO tasks VALUES ('t_2', 'lens', 'Read the news', '', NULL)")
    for task_id, profile, status, outcome, started in runs:
        connection.execute(
            "INSERT INTO task_runs (task_id, profile, status, outcome, started_at, ended_at)"
            " VALUES (?, ?, ?, ?, ?, NULL)",
            (task_id, profile, status, outcome, started),
        )
    connection.commit()
    connection.close()


class TestRecordsFromKanban(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="actledger-src-")
        self.db = os.path.join(self.dir, "kanban.db")
        self.addCleanup(shutil.rmtree, self.dir, True)
        build_db(
            self.db,
            [
                ("t_1", "forge", "done", "completed", 1792900000),
                ("t_2", "lens", "crashed", None, 1792900100),
            ],
        )

    def test_one_record_per_run(self):
        records = records_from_kanban(self.db)
        self.assertEqual(len(records), 2)

    def test_agent_comes_from_the_task_assignee(self):
        records = records_from_kanban(self.db)
        self.assertEqual([r.agent_id for r in records], ["forge", "lens"])

    def test_outcome_falls_back_to_status_when_absent(self):
        records = records_from_kanban(self.db)
        self.assertEqual(records[0].outcome, "completed")
        self.assertEqual(records[1].outcome, "crashed")

    def test_timestamp_is_utc_iso(self):
        records = records_from_kanban(self.db)
        self.assertTrue(records[0].ts.endswith("Z"))
        self.assertEqual(len(records[0].ts), 20)

    def test_verifier_stays_empty_because_kanban_never_recorded_one(self):
        records = records_from_kanban(self.db)
        self.assertTrue(all(r.verifier == "" for r in records))

    def test_task_id_is_the_data_touched(self):
        records = records_from_kanban(self.db)
        self.assertEqual(records[0].data_touched, ("t_1",))

    def test_body_is_hashed_never_stored(self):
        records = records_from_kanban(self.db)
        self.assertEqual(len(records[0].args_hash), 64)
        self.assertNotIn("go build it", records[0].args_hash)

    def test_model_override_is_carried_when_present(self):
        records = records_from_kanban(self.db)
        self.assertEqual(records[0].model_id, "model-a")
        self.assertEqual(records[1].model_id, "")

    def test_limit_is_respected(self):
        self.assertEqual(len(records_from_kanban(self.db, limit=1)), 1)

    def test_profile_filter_is_respected(self):
        records = records_from_kanban(self.db, profile="lens")
        self.assertEqual([r.agent_id for r in records], ["lens"])

    def test_missing_tables_raise_source_error(self):
        empty = os.path.join(self.dir, "empty.db")
        sqlite3.connect(empty).close()
        with self.assertRaises(SourceError):
            records_from_kanban(empty)


if __name__ == "__main__":
    unittest.main()
