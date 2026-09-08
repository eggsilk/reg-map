"""Schema CHECK constraints are the rubric's backstops (design/03, R1/R2).
These tests prove the database physically refuses the states the rubric forbids.

Run: py -m unittest tests.test_schema_constraints
"""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import build_db  # noqa: E402


def fresh_db():
    con = sqlite3.connect(":memory:")
    con.executescript(build_db.SCHEMA)
    con.execute("INSERT INTO sources VALUES ('src-x','directory','https://x','cc-by-4.0',NULL)")
    return con


class RubricBackstops(unittest.TestCase):
    def test_publishable_instrument_edge_requires_source(self):
        con = fresh_db()
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO instrument_edges (from_id,to_id,rel_type,source,publishable) "
                        "VALUES ('a','b','modeled_on',NULL,1)")
        # unpublishable without source is allowed (pending edges)
        con.execute("INSERT INTO instrument_edges (from_id,to_id,rel_type,source,publishable) "
                    "VALUES ('a','b','modeled_on',NULL,0)")

    def test_instrument_status_enum_enforced(self):
        con = fresh_db()
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO instruments (id,name_en,name_local,jurisdiction,"
                        "instrument_type,status) VALUES ('x','X','X','TR','ets','active')")

    def test_publishable_instrument_requires_status_source_and_date(self):
        con = fresh_db()
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO instruments (id,name_en,name_local,jurisdiction,"
                        "instrument_type,status,status_source,last_checked,publishable) "
                        "VALUES ('x','X','X','TR','ets','in_force',NULL,NULL,1)")
        con.execute("INSERT INTO instruments (id,name_en,name_local,jurisdiction,"
                    "instrument_type,status,status_source,last_checked,publishable) "
                    "VALUES ('x','X','X','TR','ets','in_force','src-x','2026-09-08',1)")

    def test_edge_rel_type_enum_enforced(self):
        con = fresh_db()
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO edges (from_doc,to_doc,rel_type) VALUES ('a','b','implements')")

    def test_license_enum_enforced(self):
        con = fresh_db()
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO sources VALUES ('s2','directory','https://y','cc-by-nc',NULL)")


class SeedDataLoads(unittest.TestCase):
    def test_full_build_loads_four_instruments(self):
        from common import DB_PATH
        self.assertTrue(DB_PATH.exists(), "run build_db first")
        con = sqlite3.connect(DB_PATH)
        n = con.execute("SELECT COUNT(*) FROM instruments").fetchone()[0]
        self.assertGreaterEqual(n, 4)
        pending = con.execute("SELECT COUNT(*) FROM instrument_edges WHERE publishable=0 "
                              "AND source IS NULL").fetchone()[0]
        self.assertGreaterEqual(pending, 2, "the two pending cross-border edges survive as unpublishable")


if __name__ == "__main__":
    unittest.main()
