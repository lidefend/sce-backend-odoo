# -*- coding: utf-8 -*-
"""Protect operator-editable product menu structure across module upgrades.

The business menu tree (``smart_construction_core.menu_sc_*``) is the
maintainable center/menu structure. Marking those XMLIDs noupdate before the
upgrade reloads the module data prevents the shipped XML from overwriting
manual name/sequence/parent edits, while new menu XMLIDs added in later
releases still install with noupdate=False.
"""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_data
        SET noupdate = true
        WHERE model = 'ir.ui.menu'
          AND module = 'smart_construction_core'
          AND name LIKE 'menu_sc_%'
          AND noupdate = false
        """
    )
