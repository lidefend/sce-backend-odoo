"""Product-owned empty SQL projections for optional product capabilities."""

from odoo import models, tools


_PG_TYPES = {
    "boolean": "boolean",
    "date": "date",
    "datetime": "timestamp",
    "float": "double precision",
    "integer": "integer",
    "many2one": "integer",
    "monetary": "numeric",
}


class ScOptionalProductProjection(models.AbstractModel):
    _name = "sc.optional.product.projection"
    _description = "Optional product projection boundary"

    def _create_empty_projection_view(self):
        """Create a typed product view without consulting external modules."""
        qualified_relation = "public.%s" % self._table
        self._cr.execute(
            """
            SELECT relation.relkind
              FROM pg_class relation
             WHERE relation.oid = to_regclass(%s)
            """,
            (qualified_relation,),
        )
        relation = self._cr.fetchone()
        if relation and relation[0] != "v":
            raise RuntimeError(
                "PRODUCT_PROJECTION_RELATION_CONFLICT:%s:%s"
                % (self._table, relation[0])
            )
        columns = ["NULL::integer AS id"]
        for name, field in self._fields.items():
            if name == "id" or not getattr(field, "store", False):
                continue
            pg_type = _PG_TYPES.get(getattr(field, "type", ""), "varchar")
            columns.append('NULL::%s AS "%s"' % (pg_type, name.replace('"', '')))
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            "CREATE OR REPLACE VIEW %s AS SELECT %s WHERE FALSE"
            % (self._table, ", ".join(columns))
        )
