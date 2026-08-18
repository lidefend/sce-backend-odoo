#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../_lib/common.sh"

: "${DB_NAME:?DB_NAME required}"
: "${DB_USER:?DB_USER required}"
: "${COMPOSE_FILES:?COMPOSE_FILES required}"

DB_PASSWORD=${DB_PASSWORD:-${DB_USER}}

psql_cmd() {
  compose ${COMPOSE_FILES} exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -At -c "$1"
}

fail() {
  echo "[verify.demo] FAIL item=$1 expected=$2 got=$3" >&2
  exit 1
}


check_eq() {
  local desc="$1" expected="$2" sql="$3"
  local val
  val="$(psql_cmd "${sql}")"
  if [[ "${val}" != "${expected}" ]]; then
    fail "${desc}" "${expected}" "${val}"
  else
    echo "[verify.demo] PASS item=${desc} value=${val}"
  fi
}

# Baseline checks (reuse)
check_eq "lang zh_CN active" "1" "SELECT active::int FROM res_lang WHERE code='zh_CN';"
check_eq "admin lang" "zh_CN" "SELECT lang FROM res_partner WHERE id=(SELECT partner_id FROM res_users WHERE login='admin');"
check_eq "admin tz" "Asia/Shanghai" "SELECT tz FROM res_partner WHERE id=(SELECT partner_id FROM res_users WHERE login='admin');"
check_eq "company currency is CNY" "1" "SELECT 1 FROM res_company c JOIN res_currency rc ON c.currency_id=rc.id WHERE rc.name='CNY' LIMIT 1;"
check_eq "module smart_construction_bootstrap installed" "installed" "SELECT state FROM ir_module_module WHERE name='smart_construction_bootstrap';"

# Demo/seed specific
check_eq "module smart_construction_seed installed" "installed" "SELECT state FROM ir_module_module WHERE name='smart_construction_seed';"
check_eq "module smart_construction_demo installed" "installed" "SELECT state FROM ir_module_module WHERE name='smart_construction_demo';"
check_eq "seed execution flag" "1" "SELECT COALESCE((SELECT value FROM ir_config_parameter WHERE key='sc.seed.enabled'), '0');"
check_eq "seed last_steps contains sanity" "1" "SELECT ((POSITION('sanity' IN COALESCE((SELECT value FROM ir_config_parameter WHERE key='sc.seed.last_steps'), '')) > 0)::int);"
check_eq "seed sanity ran flag" "1" "SELECT COALESCE((SELECT value FROM ir_config_parameter WHERE key='sc.seed.sanity_ran'), '0');"
check_eq "seed dictionary marker" "1" "SELECT COALESCE((SELECT value FROM ir_config_parameter WHERE key='sc.seed.dictionary'), '0');"
check_eq "seed project skeleton marker" "1" "SELECT COALESCE((SELECT value FROM ir_config_parameter WHERE key='sc.seed.project_skeleton'), '0');"
check_eq "seed boq sample marker" "10" "SELECT COALESCE((SELECT value FROM ir_config_parameter WHERE key='sc.seed.boq_count'), '0');"
check_eq "seed metrics smoke marker" "1" "SELECT COALESCE((SELECT value FROM ir_config_parameter WHERE key='sc.seed.metrics_smoke'), '0');"
check_eq "legacy global tax XMLIDs absent" "0" "SELECT COUNT(*)::text FROM ir_model_data WHERE module='smart_construction_seed' AND name IN ('tax_sale_9', 'tax_purchase_13');"
check_eq "bootstrap company contract taxes absent" "0" "SELECT COUNT(*)::text FROM account_tax t JOIN res_company c ON c.id=t.company_id JOIN account_tax_group g ON g.id=t.tax_group_id WHERE c.is_platform_bootstrap_company IS TRUE AND COALESCE(g.name->>'zh_CN', g.name->>'en_US')='合同税率';"
check_eq "registered business company tax defaults complete" "0" "WITH expected(amount) AS (VALUES (1::numeric), (3::numeric), (6::numeric), (9::numeric), (13::numeric)), registered AS (SELECT DISTINCT r.company_id FROM sc_tenant_company_registration r JOIN res_company c ON c.id=r.company_id WHERE r.active IS TRUE AND c.is_platform_bootstrap_company IS NOT TRUE) SELECT COUNT(*)::text FROM registered r CROSS JOIN expected e WHERE NOT EXISTS (SELECT 1 FROM account_tax t JOIN account_tax_group g ON g.id=t.tax_group_id WHERE t.company_id=r.company_id AND t.type_tax_use='none' AND t.amount_type='percent' AND t.amount=e.amount AND t.price_include IS FALSE AND t.active IS TRUE AND COALESCE(g.name->>'zh_CN', g.name->>'en_US')='合同税率');"
check_eq "seed partner contract exists" "1" "SELECT CASE WHEN COUNT(*) = 1 THEN '1' ELSE '0' END FROM res_partner WHERE name='Demo-合同相对方' AND active IS TRUE;"
check_eq "seed dict contract_type in exists" "1" "SELECT CASE WHEN COUNT(*) >= 1 THEN '1' ELSE '0' END FROM sc_dictionary WHERE type='contract_type' AND code='BASE_CONTRACT_IN' AND active IS TRUE;"
check_eq "seed dict contract_type out exists" "1" "SELECT CASE WHEN COUNT(*) >= 1 THEN '1' ELSE '0' END FROM sc_dictionary WHERE type='contract_type' AND code='BASE_CONTRACT_OUT' AND active IS TRUE;"
check_eq "seed dict contract_category exists" "1" "SELECT CASE WHEN COUNT(*) >= 1 THEN '1' ELSE '0' END FROM sc_dictionary WHERE type='contract_category' AND active IS TRUE;"
check_eq "demo users exist" "5" "SELECT COUNT(*)::text FROM res_users WHERE login IN ('demo_pm','demo_finance','demo_cost','demo_audit','demo_readonly') AND active IS TRUE AND share IS FALSE;"
check_eq "demo contracts exist" "1" "SELECT CASE WHEN COUNT(*) >= 1 THEN '1' ELSE '0' END FROM construction_contract WHERE project_id IS NOT NULL;"
check_eq "settlement order table exists" "sc_settlement_order" "SELECT to_regclass('sc_settlement_order');"
check_eq "canonical demo settlement exists" "1" "SELECT CASE WHEN COUNT(*) = 1 THEN '1' ELSE '0' END FROM ir_model_data d JOIN sc_settlement_order s ON s.id=d.res_id WHERE d.module='smart_construction_demo' AND d.name='sc_demo_settlement_069_payment' AND d.model='sc.settlement.order' AND s.contract_id IS NOT NULL AND s.project_id IS NOT NULL;"
check_eq "canonical demo settlement line exists" "1" "SELECT CASE WHEN COUNT(*) = 1 THEN '1' ELSE '0' END FROM ir_model_data d JOIN sc_settlement_order_line l ON l.id=d.res_id WHERE d.module='smart_construction_demo' AND d.name='sc_demo_settlement_line_069_payment' AND d.model='sc.settlement.order.line' AND l.settlement_id IS NOT NULL AND l.amount > 0;"
check_eq "canonical demo settlement amount positive" "1" "SELECT CASE WHEN COUNT(*) = 1 THEN '1' ELSE '0' END FROM ir_model_data d JOIN sc_settlement_order s ON s.id=d.res_id WHERE d.module='smart_construction_demo' AND d.name='sc_demo_settlement_069_payment' AND d.model='sc.settlement.order' AND s.amount_total > 0;"
check_eq "payment request table exists" "payment_request" "SELECT to_regclass('payment_request');"
check_eq "canonical demo payment request exists" "1" "SELECT CASE WHEN COUNT(*) = 1 THEN '1' ELSE '0' END FROM ir_model_data d JOIN payment_request pr ON pr.id=d.res_id WHERE d.module='smart_construction_demo' AND d.name='sc_demo_payment_request_069_pay' AND d.model='payment.request' AND pr.type='pay' AND pr.project_id IS NOT NULL AND pr.contract_id IS NOT NULL AND pr.settlement_id IS NOT NULL;"
check_eq "canonical demo payment within settlement remaining" "1" "SELECT CASE WHEN COUNT(*) = 1 THEN '1' ELSE '0' END FROM ir_model_data d JOIN payment_request pr ON pr.id=d.res_id JOIN sc_settlement_order s ON s.id=pr.settlement_id WHERE d.module='smart_construction_demo' AND d.name='sc_demo_payment_request_069_pay' AND d.model='payment.request' AND pr.amount <= s.remaining_amount;"


echo "[verify.demo] PASS ALL on ${DB_NAME}"
