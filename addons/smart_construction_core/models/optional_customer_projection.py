"""Fail-closed SQL views for optional customer-supplied projections."""

import hashlib
import json
import os
import re

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

_HANDOFF_REQUIRED_FIELDS = {
    "module_technical_name",
    "minimum_version",
    "provider_schema_version",
    "owner_marker",
    "relation_contract_version",
    "expected_structure_fingerprint",
    "readiness",
}
_HANDOFF_COMMENT_PREFIX = "sc_projection_owner_contract:"
_SAFE_TECHNICAL_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


def _version_tuple(value):
    parts = []
    for part in str(value or "").split("."):
        digits = "".join(character for character in part if character.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


def _relation_structure_fingerprint(cr, qualified_relation):
    cr.execute(
        """
        SELECT attribute.attname,
               pg_catalog.format_type(attribute.atttypid, attribute.atttypmod),
               attribute.attnotnull
          FROM pg_attribute attribute
         WHERE attribute.attrelid = to_regclass(%s)
           AND attribute.attnum > 0
           AND NOT attribute.attisdropped
         ORDER BY attribute.attnum
        """,
        (qualified_relation,),
    )
    payload = json.dumps(cr.fetchall(), ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_handoff_contract(table):
    raw_contract = os.environ.get("SC_EXTERNAL_PROJECTION_HANDOFF_CONTRACT", "")
    if not raw_contract.strip():
        raise RuntimeError("EXTERNAL_PROJECTION_HANDOFF_CONTRACT_MISSING:%s" % table)
    try:
        contracts = json.loads(raw_contract)
        contract = contracts[table]
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            "EXTERNAL_PROJECTION_HANDOFF_CONTRACT_INVALID:%s" % table
        ) from error
    missing = sorted(
        field
        for field in _HANDOFF_REQUIRED_FIELDS
        if field not in contract or contract[field] in ("", None)
    )
    if missing or contract.get("readiness") is not True:
        raise RuntimeError(
            "EXTERNAL_PROJECTION_HANDOFF_CONTRACT_INCOMPLETE:%s:%s"
            % (table, ",".join(missing or ["readiness"]))
        )
    if not _SAFE_TECHNICAL_NAME.fullmatch(str(contract["module_technical_name"])):
        raise RuntimeError(
            "EXTERNAL_PROJECTION_HANDOFF_CONTRACT_INVALID_MODULE:%s" % table
        )
    if not _SHA256_HEX.fullmatch(
        str(contract["expected_structure_fingerprint"])
    ):
        raise RuntimeError(
            "EXTERNAL_PROJECTION_HANDOFF_CONTRACT_INVALID_FINGERPRINT:%s" % table
        )
    return contract


def _verify_relation_owner_marker(table, relation_comment, contract):
    if not str(relation_comment or "").startswith(_HANDOFF_COMMENT_PREFIX):
        raise RuntimeError(
            "EXTERNAL_PROJECTION_HANDOFF_OWNER_MARKER_MISMATCH:%s" % table
        )
    try:
        marker = json.loads(relation_comment[len(_HANDOFF_COMMENT_PREFIX) :])
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            "EXTERNAL_PROJECTION_HANDOFF_OWNER_MARKER_INVALID:%s" % table
        ) from error
    expected = {
        "module_technical_name": contract["module_technical_name"],
        "owner_marker": contract["owner_marker"],
        "provider_schema_version": contract["provider_schema_version"],
        "relation_contract_version": contract["relation_contract_version"],
        "readiness": True,
    }
    if marker != expected:
        raise RuntimeError(
            "EXTERNAL_PROJECTION_HANDOFF_OWNER_MARKER_MISMATCH:%s" % table
        )


class ScOptionalCustomerProjection(models.AbstractModel):
    _name = "sc.optional.customer.projection"
    _description = "Optional customer projection boundary"

    def _create_empty_projection_view(self):
        """Create a typed, empty view when no external customer projection exists."""
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
            if os.environ.get("SC_ALLOW_EXTERNAL_PROJECTION_HANDOFF") == "1":
                contract = _load_handoff_contract(self._table)
                self._cr.execute(
                    """
                    SELECT latest_version
                      FROM ir_module_module
                     WHERE name = %s
                       AND state = 'installed'
                    """,
                    (contract["module_technical_name"],),
                )
                installed = self._cr.fetchone()
                if not installed or _version_tuple(installed[0]) < _version_tuple(
                    contract["minimum_version"]
                ):
                    raise RuntimeError(
                        "EXTERNAL_PROJECTION_HANDOFF_OWNER_NOT_INSTALLED:%s"
                        % self._table
                    )
                self._cr.execute(
                    "SELECT obj_description(to_regclass(%s), 'pg_class')",
                    (qualified_relation,),
                )
                owner_comment = (self._cr.fetchone() or (None,))[0]
                _verify_relation_owner_marker(
                    self._table, owner_comment, contract
                )
                actual_fingerprint = _relation_structure_fingerprint(
                    self._cr, qualified_relation
                )
                if actual_fingerprint != contract["expected_structure_fingerprint"]:
                    raise RuntimeError(
                        "EXTERNAL_PROJECTION_HANDOFF_STRUCTURE_MISMATCH:%s:%s"
                        % (self._table, actual_fingerprint)
                    )
                return
            raise RuntimeError(
                "EXTERNAL_PROJECTION_RELATION_CONFLICT:%s:%s"
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
