"""Archive product-owned projection tables before optional view cutover."""


LEGACY_PROJECTION_ARCHIVES = {
    "sc_ar_ap_project_summary": "sc_ar_ap_project_summary_legacy_17_0_0_77",
    "sc_comprehensive_cost_summary": "sc_comprehensive_cost_summary_legacy_17_0_0_77",
}


def _relation_kind(cr, relation_name):
    cr.execute(
        "SELECT relkind FROM pg_class WHERE oid = to_regclass(%s)",
        ("public.%s" % relation_name,),
    )
    row = cr.fetchone()
    return row[0] if row else None


def _quote_identifier(value):
    return '"%s"' % value.replace('"', '""')


def _dependent_relation_names(cr, relation_name):
    cr.execute(
        """
        SELECT constraint_record.conname
          FROM pg_constraint constraint_record
         WHERE constraint_record.conrelid = to_regclass(%s)
         ORDER BY constraint_record.conname
        """,
        ("public.%s" % relation_name,),
    )
    constraint_names = [row[0] for row in cr.fetchall()]
    cr.execute(
        """
        SELECT index_relation.relname
          FROM pg_index index_record
          JOIN pg_class index_relation
            ON index_relation.oid = index_record.indexrelid
          LEFT JOIN pg_constraint constraint_record
            ON constraint_record.conindid = index_record.indexrelid
         WHERE index_record.indrelid = to_regclass(%s)
           AND constraint_record.oid IS NULL
         ORDER BY index_relation.relname
        """,
        ("public.%s" % relation_name,),
    )
    index_names = [row[0] for row in cr.fetchall()]
    return constraint_names, index_names


def _archive_dependent_name(source, archive, current_name):
    if not current_name.startswith(source):
        raise RuntimeError(
            "LEGACY_PROJECTION_DEPENDENCY_NAME_UNSUPPORTED:%s:%s"
            % (source, current_name)
        )
    archived_name = "%s%s" % (archive, current_name[len(source) :])
    if len(archived_name.encode("utf-8")) > 63:
        raise RuntimeError(
            "LEGACY_PROJECTION_ARCHIVE_NAME_TOO_LONG:%s" % archived_name
        )
    return archived_name


def migrate(cr, installed_version):
    del installed_version
    for source, archive in LEGACY_PROJECTION_ARCHIVES.items():
        source_kind = _relation_kind(cr, source)
        if source_kind in (None, "v"):
            continue
        if source_kind != "r":
            raise RuntimeError(
                "LEGACY_PROJECTION_RELATION_KIND_UNSUPPORTED:%s:%s"
                % (source, source_kind)
            )
        archive_kind = _relation_kind(cr, archive)
        if archive_kind is not None:
            raise RuntimeError(
                "LEGACY_PROJECTION_ARCHIVE_ALREADY_EXISTS:%s:%s"
                % (archive, archive_kind)
            )
        constraint_names, index_names = _dependent_relation_names(cr, source)
        cr.execute(
            "ALTER TABLE %s RENAME TO %s"
            % (_quote_identifier(source), _quote_identifier(archive))
        )
        for current_name in constraint_names:
            archived_name = _archive_dependent_name(source, archive, current_name)
            cr.execute(
                "ALTER TABLE %s RENAME CONSTRAINT %s TO %s"
                % (
                    _quote_identifier(archive),
                    _quote_identifier(current_name),
                    _quote_identifier(archived_name),
                )
            )
        for current_name in index_names:
            archived_name = _archive_dependent_name(source, archive, current_name)
            cr.execute(
                "ALTER INDEX %s RENAME TO %s"
                % (
                    _quote_identifier(current_name),
                    _quote_identifier(archived_name),
                )
            )
        cr.execute(
            'COMMENT ON TABLE "%s" IS %%s' % archive,
            (
                "Archived by smart_construction_core 17.0.0.77 before "
                "optional customer projection view cutover; preserve as "
                "read-only historical evidence.",
            ),
        )
