import unittest

from sqlalchemy import Column, Float, Integer, MetaData, String, Table, create_engine, inspect

from dal.database import _drop_tables_with_schema_mismatch


class TestSchemaMismatchDrop(unittest.TestCase):
    def test_drops_table_missing_expected_column(self):
        engine = create_engine("sqlite:///:memory:")
        old_metadata = MetaData()
        Table("frame_metrics", old_metadata, Column("id", Integer, primary_key=True), Column("stream_id", String))
        old_metadata.create_all(engine)

        # Current ORM model has an extra column the live table doesn't -- e.g. person_latency_ms.
        expected_metadata = MetaData()
        expected_table = Table(
            "frame_metrics", expected_metadata,
            Column("id", Integer, primary_key=True),
            Column("stream_id", String),
            Column("person_latency_ms", Float),
        )

        with engine.connect() as conn:
            _drop_tables_with_schema_mismatch(conn, (expected_table,))
            conn.commit()
            self.assertNotIn("frame_metrics", inspect(conn).get_table_names())

    def test_keeps_table_when_schema_matches(self):
        engine = create_engine("sqlite:///:memory:")
        metadata = MetaData()
        table = Table("frame_metrics", metadata, Column("id", Integer, primary_key=True), Column("stream_id", String))
        metadata.create_all(engine)

        with engine.connect() as conn:
            _drop_tables_with_schema_mismatch(conn, (table,))
            conn.commit()
            self.assertIn("frame_metrics", inspect(conn).get_table_names())

    def test_ignores_table_that_does_not_exist_yet(self):
        engine = create_engine("sqlite:///:memory:")
        metadata = MetaData()
        table = Table("sequence_metrics", metadata, Column("id", Integer, primary_key=True))

        with engine.connect() as conn:
            # Should not raise even though the table was never created.
            _drop_tables_with_schema_mismatch(conn, (table,))


if __name__ == "__main__":
    unittest.main()
