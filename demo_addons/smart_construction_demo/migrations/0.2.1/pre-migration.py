# -*- coding: utf-8 -*-
"""Bind the historical daily-development principal to its managed demo XMLID."""


MODULE = "smart_construction_demo"
XMLID = "user_wutao_full_product"
LOGIN = "wutao"


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        "SELECT id FROM res_users WHERE login = %s ORDER BY id",
        (LOGIN,),
    )
    user_ids = [int(row[0]) for row in cr.fetchall()]
    if len(user_ids) > 1:
        raise RuntimeError("wutao must identify exactly one full-product principal")
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
        raise RuntimeError("managed wutao XMLID points at a different user")
    if existing:
        return
    cr.execute(
        """
        INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
        VALUES (%s, %s, 'res.users', %s, false)
        """,
        (MODULE, XMLID, user_ids[0]),
    )
