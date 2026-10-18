# -*- coding: utf-8 -*-
"""Bind a seed-authored demo_full principal to its new managed XMLID.

Later module data declares ``demo_full`` so a fresh install carries the
showcase principal. Databases seeded before that declaration already hold the
same login without an XMLID, and ``res_users.login`` is unique; binding the
existing row first keeps the subsequent data load an update instead of a
duplicate insert.
"""


MODULE = "smart_construction_demo"
XMLID = "user_demo_full"
LOGIN = "demo_full"


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        "SELECT id FROM res_users WHERE login = %s ORDER BY id",
        (LOGIN,),
    )
    user_ids = [int(row[0]) for row in cr.fetchall()]
    if len(user_ids) > 1:
        raise RuntimeError("demo_full must identify exactly one demo principal")
    if not user_ids:
        return

    cr.execute(
        """
        SELECT res_id
          FROM ir_model_data
         WHERE module = %s AND name = %s AND model = 'res.users'
        """,
        (MODULE, XMLID),
    )
    existing = cr.fetchone()
    if existing and int(existing[0]) != user_ids[0]:
        raise RuntimeError("managed demo_full XMLID points at a different user")
    if existing:
        return
    cr.execute(
        """
        INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
        VALUES (%s, %s, 'res.users', %s, false)
        """,
        (MODULE, XMLID, user_ids[0]),
    )
