-- Tenant isolation enforced by the database, not by application discipline.
--
-- With RLS enabled and no matching policy, a command sees zero rows / is denied by
-- default (fail closed). current_setting(..., true) returns NULL instead of raising
-- when the GUC is unset, so an unset app.tenant_id also yields zero rows rather than
-- an error or, worse, every tenant's rows.

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks    ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_read ON documents;
CREATE POLICY tenant_read ON documents FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id', true));

DROP POLICY IF EXISTS tenant_write ON documents;
CREATE POLICY tenant_write ON documents FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));

DROP POLICY IF EXISTS tenant_read ON chunks;
CREATE POLICY tenant_read ON chunks FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id', true));

DROP POLICY IF EXISTS tenant_write ON chunks;
CREATE POLICY tenant_write ON chunks FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
