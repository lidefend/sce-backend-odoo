"""Fail closed before installing the new global cost-code identity."""

from odoo.exceptions import ValidationError


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        """
        SELECT code, count(*)
          FROM project_cost_code
         WHERE code IS NOT NULL
         GROUP BY code
        HAVING count(*) > 1
         ORDER BY code
         LIMIT 1
        """
    )
    duplicate = cr.fetchone()
    if duplicate:
        raise ValidationError(
            "成本科目编码 %s 存在 %s 条重复记录，升级已停止；"
            "请先通过受控数据治理合并重复科目。" % duplicate
        )
