"""RAG-10: per-profile partial HNSW indexes, the GIN lexical index and iterative scan."""

import psycopg
from conftest import ADMIN_DSN, zero_vector_literal


def test_vector_search_uses_partial_hnsw_index_for_profile(admin_conn):
    # enable_sort is also disabled: with a small, now-populated table (corpus/meridian +
    # corpus/halcyon ingested by Phase 4), a plain Sort can look cheaper to the planner than
    # the HNSW index at this row count. Disabling both leaves the index as the only viable
    # plan, which is what this test is actually asserting exists and is usable.
    admin_conn.execute("SET LOCAL enable_seqscan = off")
    admin_conn.execute("SET LOCAL enable_sort = off")
    rows = admin_conn.execute(
        "EXPLAIN SELECT id FROM chunks WHERE profile = 'P512' "
        "ORDER BY embedding <=> %s::vector LIMIT 5",
        (zero_vector_literal(),),
    ).fetchall()
    plan = "\n".join(row[0] for row in rows)
    assert "chunks_hnsw_p512" in plan


def test_lexical_search_uses_gin_index(admin_conn):
    admin_conn.execute("SET LOCAL enable_seqscan = off")
    rows = admin_conn.execute(
        "EXPLAIN SELECT id FROM chunks WHERE fts @@ plainto_tsquery('english', 'login')"
    ).fetchall()
    plan = "\n".join(row[0] for row in rows)
    assert "chunks_fts_gin" in plan


def test_iterative_scan_defaults_to_strict_order_on_new_connection():
    with psycopg.connect(ADMIN_DSN) as fresh:
        row = fresh.execute("SHOW hnsw.iterative_scan").fetchone()
        assert row[0] == "strict_order"
