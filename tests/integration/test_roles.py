"""RAG-15: rag_owner, rag_ingest and rag_app with least-privilege grants."""


def test_rag_app_is_not_owner_of_core_tables(admin_conn):
    rows = admin_conn.execute(
        "SELECT tablename, tableowner FROM pg_tables WHERE tablename IN ('documents', 'chunks')"
    ).fetchall()
    owners = {table: owner for table, owner in rows}
    assert owners["documents"] != "rag_app"
    assert owners["chunks"] != "rag_app"


def test_rag_app_has_no_bypassrls_or_superuser(admin_conn):
    row = admin_conn.execute(
        "SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname = 'rag_app'"
    ).fetchone()
    assert row == (False, False)


def test_rag_app_cannot_write_to_documents(admin_conn):
    row = admin_conn.execute(
        """
        SELECT has_table_privilege('rag_app', 'documents', 'INSERT'),
               has_table_privilege('rag_app', 'documents', 'UPDATE'),
               has_table_privilege('rag_app', 'documents', 'DELETE')
        """
    ).fetchone()
    assert row == (False, False, False)


def test_rag_app_cannot_write_to_chunks(admin_conn):
    row = admin_conn.execute(
        """
        SELECT has_table_privilege('rag_app', 'chunks', 'INSERT'),
               has_table_privilege('rag_app', 'chunks', 'UPDATE'),
               has_table_privilege('rag_app', 'chunks', 'DELETE')
        """
    ).fetchone()
    assert row == (False, False, False)
