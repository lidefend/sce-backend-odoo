-- FIELD-ARCH-P0-01 read-only runtime snapshot.
-- Execute with psql against an isolated acceptance database. The output contains
-- field definitions only; no business record values or credentials are selected.

SELECT
    f.model,
    f.name,
    COALESCE(
        f.field_description->>'zh_CN',
        f.field_description->>'en_US',
        ''
    ),
    f.ttype,
    f.state,
    f.store,
    COALESCE(
        (
            SELECT string_agg(DISTINCT d.module, ',' ORDER BY d.module)
            FROM ir_model_data d
            WHERE d.model = 'ir.model.fields'
              AND d.res_id = f.id
        ),
        ''
    ),
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
              AND c.table_name = replace(f.model, '.', '_')
              AND c.column_name = f.name
        )
        THEN 'true'
        ELSE 'false'
    END
FROM ir_model_fields f
ORDER BY f.model, f.name;

SELECT DISTINCT
    v.model,
    match.alias_name
FROM ir_ui_view v
CROSS JOIN LATERAL regexp_matches(
    v.arch_db::text,
    '(p1_visible_[0-9a-f]{12})',
    'g'
) AS match(alias_name)
ORDER BY v.model, match.alias_name;
