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
        cr.execute('ALTER TABLE "%s" RENAME TO "%s"' % (source, archive))
        cr.execute(
            'COMMENT ON TABLE "%s" IS %%s' % archive,
            (
                "Archived by smart_construction_core 17.0.0.77 before "
                "optional customer projection view cutover; preserve as "
                "read-only historical evidence.",
            ),
        )
