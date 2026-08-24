"""RAG-08: vector/unaccent extensions and the IMMUTABLE unaccent wrapper."""


def test_immutable_unaccent_strips_diacritics(admin_conn):
    row = admin_conn.execute("SELECT immutable_unaccent(%s)", ("orçamento",)).fetchone()
    assert row[0] == "orcamento"


def test_immutable_unaccent_is_immutable(admin_conn):
    row = admin_conn.execute(
        "SELECT provolatile FROM pg_proc WHERE proname = 'immutable_unaccent'"
    ).fetchone()
    assert row[0] == "i"
