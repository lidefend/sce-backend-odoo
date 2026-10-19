#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR

# shellcheck source=../common/env.sh
source "$ROOT_DIR/scripts/common/env.sh"
# shellcheck source=../common/guard_prod.sh
source "$ROOT_DIR/scripts/common/guard_prod.sh"
# shellcheck source=../common/compose.sh
source "$ROOT_DIR/scripts/common/compose.sh"

: "${DB_NAME:?DB_NAME is required}"

guard_prod_forbid

printf '[demo.verify] db=%s\n' "$DB_NAME"

scenario="${SCENARIO:-}"
step="${STEP:-}"
known="s00_min_path s10_contract_payment s20_settlement_clearing s30_settlement_workflow s65_cost_budget_funding_surface s66_ledger_entity_surface s67_scene_pack_surface s68_cockpit_workbench_surface s69_payment_ledger_surface s70_daily_business_surface s71_governance_audit_surface s72_project_governance_surface s73_risk_settlement_surface s74_partner_supplier_surface s75_summary_projection_surface s76_workflow_compat_surface s77_data_dictionary_surface s78_project_document_wbs_surface s79_execution_structure_surface s80_execution_management_surface s85_admin_finance_surface s86_tender_rental_finance_surface s87_resource_contract_surface s88_output_invoice_surface s89_quality_safety_surface s90_users_roles showroom"

if [ -n "$scenario" ]; then
  found=0
  for s in $known; do
    if [ "$scenario" = "$s" ]; then
      found=1
      break
    fi
  done
  if [ $found -eq 0 ]; then
    echo "ERROR: unknown SCENARIO '$scenario'. known: $known"
    exit 2
  fi
fi

psql_cmd() {
  compose_dev exec -T db psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 "$@" </dev/null
}

# Showroom verification consumes the declared catalogue instead of a name
# prefix: the seed no longer writes demo/showroom markers into user-visible
# project names. Keep seed/showroom_catalog.py as the single source of truth.
showroom_names_sql="$(
  python3 - "$ROOT_DIR/demo_addons/smart_construction_demo/seed/showroom_catalog.py" <<'PY'
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("showroom_catalog", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(",".join("'" + name.replace("'", "''") + "'" for name in module.SHOWROOM_PROJECT_NAMES))
PY
)"
if [ -z "$showroom_names_sql" ]; then
  echo "ERROR: showroom catalogue is empty or unreadable" >&2
  exit 2
fi
showroom_project_filter="coalesce(p.name->>'zh_CN', p.name->>'en_US', p.name::text) in ($showroom_names_sql)"

run_check() {
  desc="$1"; scen="$2"; ok_sql="$3"; sample_sql="$4"
  if [ -n "$scenario" ] && [ "$scenario" != "$scen" ]; then
    return 0
  fi
  if psql_cmd -At -c "$ok_sql" | grep -qx ok; then
    echo "✓ $desc"
    return 0
  fi
  echo "✗ $desc"
  if [ -n "$sample_sql" ]; then
    echo "[sample]"
    psql_cmd -c "$sample_sql" || true
    echo "[/sample]"
  fi
  exit 1
}


run_check "projects >= 2" "s00_min_path" \
  "select case when count(*) >= 2 then 'ok' else 'project < 2' end from project_project;" \
  "select id, name from project_project order by id limit 20;"
run_check "BOQ nodes >= 2" "s00_min_path" \
  "select case when count(*) >= 2 then 'ok' else 'boq < 2' end from project_boq_line;" \
  "select id, name, project_id, parent_id from project_boq_line order by id limit 20;"
run_check "material plans >= 1" "s00_min_path" \
  "select case when count(*) >= 1 then 'ok' else 'material plan < 1' end from project_material_plan;" \
  "select id, name, project_id from project_material_plan order by id limit 20;"
run_check "invoices >= 2" "s00_min_path" \
  "select case when count(*) >= 2 then 'ok' else 'invoice < 2' end from account_move where move_type in ('out_invoice','out_refund');" \
  "select id, name, state, move_type, invoice_date from account_move where move_type in ('out_invoice','out_refund') order by id limit 20;"
run_check "contract record exists" "s10_contract_payment" \
  "select case when count(*) = 1 then 'ok' else 'contract missing' end from construction_contract where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_contract_out_010');" \
  "select id, subject, type, project_id, partner_id from construction_contract where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_contract_out_010');"
run_check "payment request record exists" "s10_contract_payment" \
  "select case when count(*) = 1 then 'ok' else 'payment request missing' end from payment_request where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_pay_req_010_001');" \
  "select id, type, amount, project_id, contract_id, partner_id, settlement_id from payment_request where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_pay_req_010_001');"
run_check "invoices >= 2" "s10_contract_payment" \
  "select case when count(*) >= 2 then 'ok' else 'invoices < 2' end from account_move where id in (select res_id from ir_model_data where module='smart_construction_demo' and name in ('sc_demo_invoice_s10_001','sc_demo_invoice_s10_002'));" \
  "select id, name, state, move_type, invoice_date, amount_total from account_move where id in (select res_id from ir_model_data where module='smart_construction_demo' and name in ('sc_demo_invoice_s10_001','sc_demo_invoice_s10_002')) order by id;"
run_check "payment record exists" "s20_settlement_clearing" \
  "select case when count(*) = 1 then 'ok' else 'payment missing' end from payment_request where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_payment_020_001');" \
  "select id, type, amount, project_id, contract_id, partner_id, settlement_id from payment_request where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_payment_020_001');"
run_check "settlement order exists" "s20_settlement_clearing" \
  "select case when count(*) = 1 then 'ok' else 'settlement missing' end from sc_settlement_order where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_020_001');" \
  "select id, name, state, amount_total, settlement_type from sc_settlement_order where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_020_001');"
run_check "settlement lines >= 2" "s20_settlement_clearing" \
  "select case when count(*) >= 2 then 'ok' else 'settlement lines < 2' end from sc_settlement_order_line where id in (select res_id from ir_model_data where module='smart_construction_demo' and name in ('sc_demo_settle_line_020_001','sc_demo_settle_line_020_002'));" \
  "select id, settlement_id, name, qty, price_unit, amount from sc_settlement_order_line where settlement_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_020_001') order by id;"
run_check "settlement links to at least 1 payment request" "s20_settlement_clearing" \
  "select case when count(*) >= 1 then 'ok' else 'settlement has no linked payment_request' end from payment_request where settlement_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_020_001');" \
  "select id, type, amount, settlement_id from payment_request where settlement_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_020_001') order by id;"
run_check "settlement exists and stays in draft" "s30_settlement_workflow" \
  "select case when count(*) = 1 then 'ok' else 'settlement missing or not draft' end from sc_settlement_order where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_030_001') and state = 'draft';" \
  "select id, name, state, amount_total, settlement_type from sc_settlement_order where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_030_001');"
run_check "settlement has at least one line" "s30_settlement_workflow" \
  "select case when count(*) >= 1 then 'ok' else 'settlement has no lines' end from sc_settlement_order_line where settlement_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_030_001');" \
  "select id, settlement_id, name, amount from sc_settlement_order_line where settlement_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_030_001') order by id;"
run_check "settlement links to payment requests" "s30_settlement_workflow" \
  "select case when count(*) >= 1 then 'ok' else 'settlement has no linked payment_request' end from payment_request where settlement_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_030_001');" \
  "select id, type, amount, settlement_id from payment_request where settlement_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_030_001') order by id;"
run_check "settlement amount matches line sum" "s30_settlement_workflow" \
  "select case when abs(o.amount_total - sum(l.amount)) < 0.01 then 'ok' else 'settlement amount mismatch' end from sc_settlement_order o join sc_settlement_order_line l on l.settlement_id = o.id where o.id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_030_001') group by o.amount_total;" \
  "select o.id, o.amount_total, sum(l.amount) as line_sum from sc_settlement_order o join sc_settlement_order_line l on l.settlement_id = o.id where o.id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_settlement_030_001') group by o.id, o.amount_total;"
run_check "cost budget and allocation records exist" "s65_cost_budget_funding_surface" \
  "select case when (select count(*) from project_budget where name='主体结构成本控制版' and version='2025-CTRL-V1') = 1 and (select count(*) from project_budget_boq_line where name='三层梁板钢筋制安') = 1 and (select count(*) from project_budget_cost_alloc where budget_boq_line_id in (select id from project_budget_boq_line where name='三层梁板钢筋制安')) = 2 then 'ok' else 'budget records missing' end;" \
  "select b.id, b.name, b.version, b.amount_revenue_target, b.amount_cost_target from project_budget b where b.name='主体结构成本控制版';"
run_check "cost ledger progress and funding records exist" "s65_cost_budget_funding_surface" \
  "select case when (select count(*) from construction_work_breakdown where code in ('01','0101') and project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_065_cost_funding')) = 2 and (select count(*) from project_cost_period where period='2025-08' and locked=false and project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_065_cost_funding')) >= 1 and (select count(*) from project_cost_ledger where amount=218400.0 and project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_065_cost_funding')) = 1 and (select count(*) from project_progress_entry where note='三层梁板钢筋本期进度计量草稿。' and state='draft' and project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_065_cost_funding')) = 1 and (select count(*) from project_funding_baseline where total_amount=5000000.0 and state='active' and id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_funding_baseline_065')) = 1 then 'ok' else 'cost ledger/progress/funding missing' end;" \
  "select 'cost_ledger' as kind, id, note, amount::text as value from project_cost_ledger where amount=218400.0 and project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_065_cost_funding') union all select 'progress', id, note, progress_rate::text from project_progress_entry where note='三层梁板钢筋本期进度计量草稿。' and project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_065_cost_funding') union all select 'funding', id, state, total_amount::text from project_funding_baseline where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_funding_baseline_065');"
run_check "receipt invoice and output ledger records exist" "s66_ledger_entity_surface" \
  "select case when (select count(*) from sc_receipt_invoice_line where legacy_invoice_line_id='S66-RIL-001') = 1 and (select count(*) from sc_output_invoice_ledger where invoice_no='FP-2025-001' and source_model='sc.receipt.invoice.line') = 1 then 'ok' else 'receipt invoice ledger missing' end;" \
  "select id, invoice_no, source_model, invoice_amount, current_receipt_amount from sc_output_invoice_ledger where invoice_no='FP-2025-001';"
run_check "contract ledger records exist" "s66_ledger_entity_surface" \
  "select case when (select count(*) from sc_income_contract_ledger where contract_no='HT-2025-001') = 1 and (select count(*) from sc_expense_contract_ledger where contract_no='HT-2025-002') = 1 then 'ok' else 'contract ledger missing' end;" \
  "select 'income' as kind, id, contract_no, contract_name, amount_total from sc_income_contract_ledger where contract_no='HT-2025-001' union all select 'expense', id, contract_no, contract_name, amount_total from sc_expense_contract_ledger where contract_no='HT-2025-002';"
run_check "business entity exists without migration carriers" "s66_ledger_entity_surface" \
  "select case when count(*) = 1 then 'ok' else 'business entity missing' end from sc_business_entity where name='德阳项目经营载体' and entity_type='project_carrier' and active=true;" \
  "select id, name, entity_type, company_id, partner_id, active from sc_business_entity where name='德阳项目经营载体';"
run_check "scene capability records exist" "s67_scene_pack_surface" \
  "select case when (select count(*) from sc_capability_group where key='demo_ops_surface') = 1 and (select count(*) from sc_capability where key='demo.ops.dashboard' and status='ga') = 1 and (select count(*) from sc_scene where code='s67_demo_ops_scene' and state='published') = 1 and (select count(*) from sc_scene_tile where scene_id in (select id from sc_scene where code='s67_demo_ops_scene')) = 1 and (select count(*) from sc_scene_version where scene_id in (select id from sc_scene where code='s67_demo_ops_scene') and version='v1.0') = 1 then 'ok' else 'scene capability records missing' end;" \
  "select s.id, s.code, s.state, s.version, v.id as version_id from sc_scene s left join sc_scene_version v on v.id = s.active_version_id where s.code='s67_demo_ops_scene';"
run_check "pack registry records exist" "s67_scene_pack_surface" \
  "select case when (select count(*) from sc_pack_registry where pack_id='s67.demo.surface.pack' and channel='stable') = 1 and (select count(*) from sc_pack_installation where pack_id in (select id from sc_pack_registry where pack_id='s67.demo.surface.pack') and status='installed') = 1 then 'ok' else 'pack records missing' end;" \
  "select r.id, r.pack_id, r.pack_version, i.status from sc_pack_registry r left join sc_pack_installation i on i.pack_id = r.id where r.pack_id='s67.demo.surface.pack';"
run_check "dashboard cockpit facts exist" "s68_cockpit_workbench_surface" \
  "select case when (select count(*) from sc_dashboard_cockpit_fact where name like '%' and fact_type in ('fund_cockpit', 'cost_cockpit')) = 2 then 'ok' else 'dashboard facts missing' end;" \
  "select id, name, fact_type, project_id, amount, metric_value, source_model, source_res_id, state from sc_dashboard_cockpit_fact where name like '%' order by id;"
run_check "workbench items exist" "s68_cockpit_workbench_surface" \
  "select case when (select count(*) from sc_workbench_item where name like '%' and fact_type in ('my_todo', 'my_approval', 'recent_visit')) = 3 then 'ok' else 'workbench items missing' end;" \
  "select id, name, fact_type, priority, todo_deadline, source_model, source_res_id, state from sc_workbench_item where name like '%' order by id;"
run_check "payment ledger chain exists" "s69_payment_ledger_surface" \
  "select case when (select count(*) from sc_settlement_order where name='JS-2025-001' and state='approve') = 1 and (select count(*) from payment_request where name='FK-2025-001' and state in ('approved','done')) = 1 and (select count(*) from payment_ledger l join payment_request pr on pr.id = l.payment_request_id where pr.name='FK-2025-001' and l.amount=120000.0 and l.state='posted') = 1 then 'ok' else 'payment ledger chain missing' end;" \
  "select l.id, l.ref, l.amount, pr.name as request_name, pr.state as request_state, s.name as settlement_name, s.state as settlement_state from payment_ledger l join payment_request pr on pr.id = l.payment_request_id left join sc_settlement_order s on s.id = pr.settlement_id where pr.name='FK-2025-001';"
run_check "material catalog and price exist" "s70_daily_business_surface" \
  "select case when (select count(*) from sc_material_catalog where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_material_catalog_070_steel')) = 1 and (select count(*) from sc_material_price where id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_material_price_070_steel_quote')) = 1 then 'ok' else 'material records missing' end;" \
  "select c.id, c.name, p.unit_price from sc_material_catalog c left join sc_material_price p on p.material_catalog_id = c.id where c.id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_material_catalog_070_steel');"
run_check "finance daily records exist" "s70_daily_business_surface" \
  "select case when (select count(*) from sc_expense_claim where name='BX-2025-001') = 1 and (select count(*) from sc_receipt_income where name='SK-2025-002') = 1 and (select count(*) from sc_payment_execution where name='FKZX-2025-001') = 1 and (select count(*) from sc_treasury_reconciliation where name='DZ-2025-001') = 1 then 'ok' else 'finance records missing' end;" \
  "select 'expense' as kind, id, name, state from sc_expense_claim where name='BX-2025-001' union all select 'receipt', id, name, state from sc_receipt_income where name='SK-2025-002' union all select 'payment', id, name, state from sc_payment_execution where name='FKZX-2025-001' union all select 'treasury', id, name, state from sc_treasury_reconciliation where name='DZ-2025-001';"
run_check "invoice tax and diary records exist" "s70_daily_business_surface" \
  "select case when (select count(*) from sc_invoice_registration where name='FP-2025-002') = 1 and (select count(*) from sc_tax_deduction_registration where name='DKDJ-2025-001') = 1 and (select count(*) from sc_construction_diary where name='RZ-2025-001') = 1 then 'ok' else 'invoice/tax/diary records missing' end;" \
  "select 'invoice' as kind, id, name, state from sc_invoice_registration where name='FP-2025-002' union all select 'tax', id, name, state from sc_tax_deduction_registration where name='DKDJ-2025-001' union all select 'diary', id, name, state from sc_construction_diary where name='RZ-2025-001';"
run_check "approval governance seeds exist" "s71_governance_audit_surface" \
  "select case when (select count(*) from sc_approval_policy where code='payment_request_approval' and target_model='payment.request' and runtime_state='tier_validation') = 1 and (select count(*) from sc_approval_step s join sc_approval_policy p on p.id=s.policy_id where p.code='payment_request_approval' and s.approval_scope_key='finance_manager') >= 1 and (select count(*) from sc_approval_scope where scope_key='finance_manager') = 1 then 'ok' else 'approval governance seed missing' end;" \
  "select p.id, p.code, p.target_model, p.runtime_state, s.name as step_name, s.approval_scope_key from sc_approval_policy p left join sc_approval_step s on s.policy_id=p.id where p.code='payment_request_approval';"
run_check "scene governance audit records exist" "s71_governance_audit_surface" \
  "select case when (select count(*) from sc_scene_validation where status='pass' and scene_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_scene_067_demo_ops')) >= 1 and (select count(*) from sc_scene_audit_log where event in ('publish','update_pref') and scene_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_scene_067_demo_ops')) >= 2 and (select count(*) from sc_capability_audit_log where source_pack_id='s67.demo.surface.pack') >= 1 then 'ok' else 'scene governance records missing' end;" \
  "select 'validation' as kind, id, status as value from sc_scene_validation where scene_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_scene_067_demo_ops') union all select 'scene_audit', id, event from sc_scene_audit_log where scene_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_scene_067_demo_ops') union all select 'capability_audit', id, event from sc_capability_audit_log where source_pack_id='s67.demo.surface.pack';"
run_check "user preference and audit log exist" "s71_governance_audit_surface" \
  "select case when (select count(*) from sc_user_preference where user_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='user_demo_e2e_smoke') and default_scene_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_scene_067_demo_ops')) = 1 and (select count(*) from sc_audit_log where event_code='S71_PAYMENT_REQUEST_REVIEW' and trace_id='AUD-2025-001') = 1 then 'ok' else 'preference audit records missing' end;" \
  "select 'preference' as kind, id, user_id, default_scene_id, null as event_code, null as trace_id from sc_user_preference where user_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='user_demo_e2e_smoke') union all select 'audit', id, actor_uid, project_id, event_code, trace_id from sc_audit_log where trace_id='AUD-2025-001';"
run_check "project stage and next action rules exist" "s72_project_governance_surface" \
  "select case when (select count(*) from sc_project_stage_requirement_item where id in (select res_id from ir_model_data where module='smart_construction_demo' and name in ('sc_demo_stage_requirement_072_funding','sc_demo_stage_requirement_072_progress')) and lifecycle_state='in_progress' and active is true) = 2 and (select count(*) from sc_project_next_action_rule where id in (select res_id from ir_model_data where module='smart_construction_demo' and name in ('sc_demo_next_action_rule_072_payment','sc_demo_next_action_rule_072_cost')) and lifecycle_state='in_progress' and active is true) = 2 then 'ok' else 'project governance rules missing' end;" \
  "select 'requirement' as kind, id, name, lifecycle_state, active from sc_project_stage_requirement_item where id in (select res_id from ir_model_data where module='smart_construction_demo' and name in ('sc_demo_stage_requirement_072_funding','sc_demo_stage_requirement_072_progress')) union all select 'next_action', id, name, lifecycle_state, active from sc_project_next_action_rule where id in (select res_id from ir_model_data where module='smart_construction_demo' and name in ('sc_demo_next_action_rule_072_payment','sc_demo_next_action_rule_072_cost'));"
run_check "formal project member assignment exists" "s72_project_governance_surface" \
  "select case when count(*) = 1 then 'ok' else 'project member assignment missing' end from sc_project_member_assignment where project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_065_cost_funding') and user_id in (select res_id from ir_model_data where module='base' and name='user_admin') and source='manual' and active=true;" \
  "select id, project_id, user_id, source, note, active from sc_project_member_assignment where project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_065_cost_funding');"
run_check "operating metrics projection is published" "s72_project_governance_surface" \
  "select case when to_regclass('sc_operating_metrics_project') is not null and (select count(*) from ir_act_window where res_model='sc.operating.metrics.project') >= 1 then 'ok' else 'operating metrics projection missing' end;" \
  "select to_regclass('sc_operating_metrics_project') as relation, count(*) as action_count from ir_act_window where res_model='sc.operating.metrics.project';"
run_check "project risk projection exists" "s73_risk_settlement_surface" \
  "select case when (select count(*) from project_risk where project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_073_risk') and health_state='risk') = 1 then 'ok' else 'project risk projection missing' end;" \
  "select id, project_id, name, health_state from project_risk where project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_073_risk');"
run_check "risk actions exist" "s73_risk_settlement_surface" \
  "select case when (select count(*) from project_risk_action where project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_073_risk') and state in ('claimed','escalated')) = 2 then 'ok' else 'risk actions missing' end;" \
  "select id, name, project_id, state, risk_level, owner_id from project_risk_action where project_id in (select res_id from ir_model_data where module='smart_construction_demo' and name='sc_demo_project_073_risk') order by id;"
run_check "compatible settlement records exist" "s73_risk_settlement_surface" \
  "select case when (select count(*) from project_settlement where name='JS-2025-002' and state='confirmed' and amount=360000.0) = 1 and (select count(*) from project_settlement_line where settlement_id in (select id from project_settlement where name='JS-2025-002')) = 2 then 'ok' else 'compatible settlement missing' end;" \
  "select s.id, s.name, s.state, s.amount, count(l.id) as line_count from project_settlement s left join project_settlement_line l on l.settlement_id=s.id where s.name='JS-2025-002' group by s.id, s.name, s.state, s.amount;"
run_check "supplier type and partner records exist" "s74_partner_supplier_surface" \
  "select case when (select count(*) from sc_supplier_type where code in ('service','equipment') and active is true) = 2 and (select count(*) from res_partner where name='四川智建咨询服务有限公司' and supplier_rank > 0 and customer_rank > 0 and sc_supplier_type='service') = 1 then 'ok' else 'supplier partner records missing' end;" \
  "select p.id, p.name, p.supplier_rank, p.customer_rank, p.sc_supplier_type, p.sc_supplier_type_label, p.sc_region from res_partner p where p.name='四川智建咨询服务有限公司';"
run_check "invoice and expense summaries have output" "s75_summary_projection_surface" \
  "select case when (select count(*) from sc_invoice_category_summary where manual_invoice_count > 0) >= 1 and (select count(*) from sc_expense_reimbursement_summary where manual_count > 0) >= 1 then 'ok' else 'invoice/expense summaries missing' end;" \
  "select 'invoice' as kind, id, display_name, amount_total as amount, invoice_count as record_count from sc_invoice_category_summary where manual_invoice_count > 0 union all select 'expense', id, display_name, amount, claim_count from sc_expense_reimbursement_summary where manual_count > 0 order by kind, id limit 10;"
run_check "salary summary has output and company operation projection is published" "s75_summary_projection_surface" \
  "select case when (select count(*) from sc_salary_summary where manual_count > 0) >= 1 and to_regclass('sc_company_operation_summary') is not null and (select count(*) from ir_act_window where res_model='sc.company.operation.summary') >= 1 then 'ok' else 'salary/company summaries missing' end;" \
  "select 'salary' as kind, id, display_name, net_salary as amount, document_count as record_count from sc_salary_summary where manual_count > 0 union all select 'company_projection', null, to_regclass('sc_company_operation_summary')::text, null, count(*) from ir_act_window where res_model='sc.company.operation.summary';"
run_check "workflow compatibility chain exists" "s76_workflow_compat_surface" \
  "select case when (select count(*) from sc_workflow_def where code='s76_payment_request_compat' and state='published') = 1 and (select count(*) from sc_workflow_node where workflow_def_id in (select id from sc_workflow_def where code='s76_payment_request_compat')) = 3 and (select count(*) from sc_workflow_instance where workflow_def_id in (select id from sc_workflow_def where code='s76_payment_request_compat') and state='running') = 1 then 'ok' else 'workflow chain missing' end;" \
  "select d.id as def_id, d.code, d.state, i.id as instance_id, i.state as instance_state, n.code as current_node from sc_workflow_def d left join sc_workflow_instance i on i.workflow_def_id=d.id left join sc_workflow_node n on n.id=i.current_node_id where d.code='s76_payment_request_compat';"
run_check "workflow workitem and logs exist" "s76_workflow_compat_surface" \
  "select case when (select count(*) from sc_workflow_workitem where instance_id in (select id from sc_workflow_instance where workflow_def_id in (select id from sc_workflow_def where code='s76_payment_request_compat')) and status='todo') = 1 and (select count(*) from sc_workflow_log where instance_id in (select id from sc_workflow_instance where workflow_def_id in (select id from sc_workflow_def where code='s76_payment_request_compat'))) = 2 then 'ok' else 'workflow workitem/log missing' end;" \
  "select 'workitem' as kind, id, status as value from sc_workflow_workitem where instance_id in (select id from sc_workflow_instance where workflow_def_id in (select id from sc_workflow_def where code='s76_payment_request_compat')) union all select 'log', id, action from sc_workflow_log where instance_id in (select id from sc_workflow_instance where workflow_def_id in (select id from sc_workflow_def where code='s76_payment_request_compat')) order by kind, id;"
run_check "project dictionary hierarchy exists" "s77_data_dictionary_surface" \
  "select case when (select count(*) from project_dictionary where code in ('CIVIL','STRUCT','QI-REBAR','SUB-REBAR-INSTALL')) = 4 and (select count(*) from project_dictionary sub join project_dictionary qi on qi.id=sub.parent_id join project_dictionary ch on ch.id=qi.parent_id join project_dictionary dis on dis.id=ch.parent_id where sub.code='SUB-REBAR-INSTALL' and qi.code='QI-REBAR' and ch.code='STRUCT' and dis.code='CIVIL' and sub.type='sub_item' and sub.level=4) = 1 then 'ok' else 'dictionary hierarchy missing' end;" \
  "select id, code, name, type, parent_id, level, full_name from project_dictionary where code in ('CIVIL','STRUCT','QI-REBAR','SUB-REBAR-INSTALL') order by level, sequence;"
run_check "signup throttle policy and GC exist without demo counters" "s77_data_dictionary_surface" \
  "select case when (select count(*) from sc_signup_throttle where key like 's77:signup:%') = 0 and (select count(*) from ir_cron c join ir_act_server s on s.id=c.ir_actions_server_id join ir_model m on m.id=s.model_id where m.model='sc.signup.throttle' and c.active and s.code='model.gc_expired()') = 1 and (select count(*) from ir_config_parameter where key in ('sc.signup.ratelimit.window_sec','sc.signup.ratelimit.max_per_ip','sc.signup.ratelimit.max_per_email','sc.signup.ratelimit.gc_days') and nullif(value, '') is not null) = 4 then 'ok' else 'signup throttle policy/GC boundary invalid' end;" \
  "select c.id, c.cron_name, c.active, s.code from ir_cron c join ir_act_server s on s.id=c.ir_actions_server_id join ir_model m on m.id=s.model_id where m.model='sc.signup.throttle';"
run_check "project WBS compatibility hierarchy exists" "s78_project_document_wbs_surface" \
  "select case when (select count(*) from construction_work_breakdown where code in ('SINGLE','UNIT','SUBDIV','INSP-001')) = 4 and (select count(*) from construction_work_breakdown insp join construction_work_breakdown sub on sub.id=insp.parent_id join construction_work_breakdown unit on unit.id=sub.parent_id join construction_work_breakdown single on single.id=unit.parent_id where insp.code='INSP-001' and sub.code='SUBDIV' and unit.code='UNIT' and single.code='SINGLE' and insp.level_type='work_package' and sub.level_type='summary' and unit.level_type='control_account' and single.level_type='phase') = 1 then 'ok' else 'WBS management hierarchy missing' end;" \
  "select id, code, name, level_type, parent_id, level from construction_work_breakdown where code in ('SINGLE','UNIT','SUBDIV','INSP-001') order by level, sequence;"
run_check "project documents with attachment exist" "s78_project_document_wbs_surface" \
  "select case when (select count(*) from sc_project_document where name in ('临边防护专项安全资料','三层梁板钢筋隐蔽验收记录') and wbs_id is not null and task_id is not null and doc_subtype_id is not null) = 2 and (select count(*) from sc_project_document d join sc_project_document_attachment_rel rel on rel.document_id=d.id join ir_attachment a on a.id=rel.attachment_id where d.name='三层梁板钢筋隐蔽验收记录' and d.state='done' and a.name='quality-acceptance-note.txt') = 1 then 'ok' else 'project documents missing' end;" \
  "select d.id, d.name, d.document_kind, d.state, d.wbs_id, d.task_id, count(rel.attachment_id) as attachment_count from sc_project_document d left join sc_project_document_attachment_rel rel on rel.document_id=d.id where d.name like '%' group by d.id, d.name, d.document_kind, d.state, d.wbs_id, d.task_id order by d.name;"
run_check "independent location and contract dimensions exist" "s79_execution_structure_surface" \
  "select case when (select count(*) from construction_location_breakdown where code in ('SITE','BUILDING','FIRE-ZONE')) = 3 and (select count(*) from construction_location_breakdown zone join construction_location_breakdown building on building.id=zone.parent_id join construction_location_breakdown site on site.id=building.parent_id where zone.code='FIRE-ZONE' and building.code='BUILDING' and site.code='SITE') = 1 and (select count(*) from construction_contract_section where code='SECTION-FIRE') = 1 then 'ok' else 'execution dimensions missing' end;" \
  "select id, code, name, location_type, parent_id from construction_location_breakdown where code in ('SITE','BUILDING','FIRE-ZONE','SECTION-FIRE') order by parent_path, sequence;"
run_check "BOQ is allocated to execution scope" "s79_execution_structure_surface" \
  "select case when (select count(*) from project_boq_allocation a join project_boq_line b on b.id=a.boq_line_id join construction_execution_scope s on s.id=a.execution_scope_id where b.code='BOQ-FIRE-PIPE' and s.location_id in (select id from construction_location_breakdown where code='FIRE-ZONE') and s.contract_section_id in (select id from construction_contract_section where code='SECTION-FIRE') and s.wbs_id is not null and a.allocation_ratio=100.0 and b.amount=59200.0) = 1 then 'ok' else 'BOQ execution allocation missing' end;" \
  "select b.code, b.quantity, b.amount, a.allocation_ratio, s.wbs_id, s.location_id, s.contract_section_id from project_boq_allocation a join project_boq_line b on b.id=a.boq_line_id join construction_execution_scope s on s.id=a.execution_scope_id where b.code='BOQ-FIRE-PIPE';"
run_check "material execution chain exists" "s80_execution_management_surface" \
  "select case when (select count(*) from sc_material_purchase_request where name='CGSQ-2025-001') = 1 and (select count(*) from sc_material_acceptance where name='YS-2025-001' and state='accepted') = 1 and (select count(*) from sc_material_inbound where name='RK-2025-001' and state='received') = 1 and (select count(*) from sc_material_outbound where name='CK-2025-002' and state='issued') = 1 and (select count(*) from sc_material_settlement where name='JS-2025-003' and state='confirmed') = 1 then 'ok' else 'material chain missing' end;" \
  "select 'request' as kind, id, name, state from sc_material_purchase_request where name='CGSQ-2025-001' union all select 'acceptance', id, name, state from sc_material_acceptance where name='YS-2025-001' union all select 'inbound', id, name, state from sc_material_inbound where name='RK-2025-001' union all select 'outbound', id, name, state from sc_material_outbound where name='CK-2025-002' union all select 'settlement', id, name, state from sc_material_settlement where name='JS-2025-003';"
run_check "plan quality safety records exist" "s80_execution_management_surface" \
  "select case when (select count(*) from sc_plan where name='主体结构月度执行计划') = 1 and (select count(*) from sc_plan_report where name='周计划进度汇报') = 1 and (select count(*) from sc_quality_issue where name='钢筋保护层垫块局部缺失' and state='closed') = 1 and (select count(*) from sc_safety_issue where name='楼层临边防护局部松动' and state='closed') = 1 then 'ok' else 'plan/quality/safety missing' end;" \
  "select 'plan' as kind, id, name, state from sc_plan where name='主体结构月度执行计划' union all select 'quality', id, name, state from sc_quality_issue where name='钢筋保护层垫块局部缺失' union all select 'safety', id, name, state from sc_safety_issue where name='楼层临边防护局部松动';"
run_check "labor and equipment records exist" "s80_execution_management_surface" \
  "select case when (select count(*) from sc_labor_plan where name='LWP-2025-001') = 1 and (select count(*) from sc_labor_request where name='LWSQ-2025-001') = 1 and (select count(*) from sc_attendance_checkin where name='KQ-2025-001' and state='confirmed') = 1 and (select count(*) from sc_equipment_plan where name='SBP-2025-001') = 1 and (select count(*) from sc_equipment_request where name='SBSQ-2025-001') = 1 and (select count(*) from sc_equipment_usage where name='SBSY-2025-001' and state='confirmed') = 1 then 'ok' else 'labor/equipment missing' end;" \
  "select 'labor_plan' as kind, id, name, state from sc_labor_plan where name='LWP-2025-001' union all select 'labor_request', id, name, state from sc_labor_request where name='LWSQ-2025-001' union all select 'attendance', id, name, state from sc_attendance_checkin where name='KQ-2025-001' union all select 'equipment_plan', id, name, state from sc_equipment_plan where name='SBP-2025-001' union all select 'equipment_request', id, name, state from sc_equipment_request where name='SBSQ-2025-001' union all select 'equipment_usage', id, name, state from sc_equipment_usage where name='SBSY-2025-001';"
run_check "fund and financing records exist" "s85_admin_finance_surface" \
  "select case when (select count(*) from sc_fund_account where name='项目监管户') = 1 and (select count(*) from sc_financing_loan where name='DK-2025-001' and state='confirmed') = 1 then 'ok' else 'fund/financing missing' end;" \
  "select 'fund_account' as kind, id, name, state from sc_fund_account where name='项目监管户' union all select 'financing_loan', id, name, state from sc_financing_loan where name='DK-2025-001';"
run_check "admin and payroll records exist" "s85_admin_finance_surface" \
  "select case when (select count(*) from sc_document_admin_document where name in ('安全生产许可证登记','合同原件借阅申请') and state='done') = 2 and (select count(*) from sc_office_admin_document where name in ('项目经理调休审批','项目章使用审批') and state='done') = 2 and (select count(*) from sc_hr_payroll_document where name in ('项目管理人员工资登记','节点奖登记') and state='done') = 2 then 'ok' else 'admin/payroll missing' end;" \
  "select 'document' as kind, id, name, state from sc_document_admin_document where name like '%' union all select 'office', id, name, state from sc_office_admin_document where name like '%' union all select 'payroll', id, name, state from sc_hr_payroll_document where name like '%';"
run_check "subcontract chain exists" "s85_admin_finance_surface" \
  "select case when (select count(*) from sc_subcontract_plan where name='FBJH-2025-001' and state='approved') = 1 and (select count(*) from sc_subcontract_request where name='FBSQ-2025-001' and state='approved') = 1 and (select count(*) from sc_subcontract_register where name='FBDJ-2025-001' and state='active') = 1 and (select count(*) from sc_subcontract_settlement where name='FBJS-2025-001' and state='confirmed') = 1 and (select count(*) from sc_subcontract_price where name='FBJ-2025-001' and state='active') = 1 then 'ok' else 'subcontract chain missing' end;" \
  "select 'plan' as kind, id, name, state from sc_subcontract_plan where name='FBJH-2025-001' union all select 'request', id, name, state from sc_subcontract_request where name='FBSQ-2025-001' union all select 'register', id, name, state from sc_subcontract_register where name='FBDJ-2025-001' union all select 'settlement', id, name, state from sc_subcontract_settlement where name='FBJS-2025-001' union all select 'price', id, name, state from sc_subcontract_price where name='FBJ-2025-001';"
run_check "tender chain exists" "s86_tender_rental_finance_surface" \
  "select case when (select count(*) from tender_bid where name='TB-2025-001' and state='won') = 1 and (select count(*) from tender_bid_line where bid_id in (select id from tender_bid where name='TB-2025-001')) = 2 and (select count(*) from tender_doc_purchase where bid_id in (select id from tender_bid where name='TB-2025-001') and state='approved') = 1 and (select count(*) from tender_opening where bid_id in (select id from tender_bid where name='TB-2025-001') and result='won') = 1 and (select count(*) from tender_guarantee where bid_id in (select id from tender_bid where name='TB-2025-001') and state='confirmed') = 2 then 'ok' else 'tender chain missing' end;" \
  "select id, name, tender_name, state, bid_amount from tender_bid where name='TB-2025-001';"
run_check "fund deposit and adjustment records exist" "s86_tender_rental_finance_surface" \
  "select case when (select count(*) from sc_fund_account_operation where name in ('ZJLS-2025-001','ZJLS-2025-002')) = 2 and (select count(*) from sc_expense_claim where name in ('BX-2025-002','BX-2025-003') and state='done') = 2 and (select count(*) from sc_settlement_adjustment where name='TZ-2025-001' and state='confirmed') = 1 then 'ok' else 'fund/deposit/adjustment missing' end;" \
  "select 'fund_op' as kind, id, name, state from sc_fund_account_operation where name in ('ZJLS-2025-001','ZJLS-2025-002') union all select 'deposit', id, name, state from sc_expense_claim where name in ('BX-2025-002','BX-2025-003') union all select 'adjustment', id, name, state from sc_settlement_adjustment where name='TZ-2025-001';"
run_check "material rental chain exists" "s86_tender_rental_finance_surface" \
  "select case when (select count(*) from sc_material_rental_plan where name='ZLJH-2025-001' and state='approved') = 1 and (select count(*) from sc_material_rental_order where name='ZLD-2025-001' and state='settled') = 1 and (select count(*) from sc_material_rental_settlement where name='ZLJS-2025-001' and state='paid') = 1 then 'ok' else 'material rental chain missing' end;" \
  "select 'plan' as kind, id, name, state from sc_material_rental_plan where name='ZLJH-2025-001' union all select 'order', id, name, state from sc_material_rental_order where name='ZLD-2025-001' union all select 'settlement', id, name, state from sc_material_rental_settlement where name='ZLJS-2025-001';"
run_check "labor resource records exist" "s87_resource_contract_surface" \
  "select case when (select count(*) from sc_labor_usage where name='LW-2025-001' and state='confirmed') = 1 and (select count(*) from sc_labor_settlement where name='LWJS-2025-001' and state='confirmed') = 1 and (select count(*) from sc_labor_settlement_line where settlement_id in (select id from sc_labor_settlement where name='LWJS-2025-001')) = 1 and (select count(*) from sc_labor_price where name='LWJ-2025-001' and state='active') = 1 then 'ok' else 'labor resource records missing' end;" \
  "select 'usage' as kind, id, name, state from sc_labor_usage where name='LW-2025-001' union all select 'settlement', id, name, state from sc_labor_settlement where name='LWJS-2025-001' union all select 'price', id, name, state from sc_labor_price where name='LWJ-2025-001';"
run_check "equipment resource records exist" "s87_resource_contract_surface" \
  "select case when (select count(*) from sc_equipment_settlement where name='SBJS-2025-001' and state='confirmed') = 1 and (select count(*) from sc_equipment_settlement_line where settlement_id in (select id from sc_equipment_settlement where name='SBJS-2025-001')) = 1 and (select count(*) from sc_equipment_price where name='SBJ-2025-001' and state='active') = 1 then 'ok' else 'equipment resource records missing' end;" \
  "select 'settlement' as kind, id, name, state from sc_equipment_settlement where name='SBJS-2025-001' union all select 'price', id, name, state from sc_equipment_price where name='SBJ-2025-001';"
run_check "contract records exist" "s87_resource_contract_surface" \
  "select case when (select count(*) from sc_general_contract where name='HT-2025-003' and state='signed') = 1 and (select count(*) from sc_contract_event where event_no in ('BG-2025-001','BG-2025-002') and state in ('approved','done')) = 2 then 'ok' else 'contract records missing' end;" \
  "select 'general_contract' as kind, id, name, state from sc_general_contract where name='HT-2025-003' union all select 'contract_event', id, name, state from sc_contract_event where event_no in ('BG-2025-001','BG-2025-002');"
run_check "output invoice ledger record exists" "s88_output_invoice_surface" \
  "select case when (select count(*) from sc_invoice_registration where name='FP-2025-003' and direction='output' and state='registered') = 1 and (select count(*) from sc_output_invoice_ledger where invoice_no='FP-2025-003' and adjustment_kind='normal') = 1 then 'ok' else 'output invoice ledger missing' end;" \
  "select id, invoice_no, adjustment_kind, invoice_amount, amount_no_tax, tax_amount from sc_output_invoice_ledger where invoice_no='FP-2025-003';"
run_check "output invoice adjustment record exists" "s88_output_invoice_surface" \
  "select case when (select count(*) from sc_output_invoice_adjustment where name='FPCH-2025-001' and state='draft' and invoice_no='FP-2025-003' and red_flush_invoice_amount < 0) = 1 then 'ok' else 'output invoice adjustment missing' end;" \
  "select id, name, state, invoice_no, original_invoice_amount, red_flush_invoice_amount from sc_output_invoice_adjustment where name='FPCH-2025-001';"
run_check "quality standard and loop records exist" "s89_quality_safety_surface" \
  "select case when (select count(*) from sc_check_standard where name='主体结构质量检查标准') = 1 and (select count(*) from sc_check_standard_item where name='钢筋间距和保护层厚度') = 1 and (select count(*) from sc_quality_issue where name='梁底钢筋保护层偏差' and state='closed') = 1 and (select count(*) from sc_quality_rectification where issue_id in (select id from sc_quality_issue where name='梁底钢筋保护层偏差')) = 1 and (select count(*) from sc_quality_recheck where issue_id in (select id from sc_quality_issue where name='梁底钢筋保护层偏差') and result='passed') = 1 then 'ok' else 'quality records missing' end;" \
  "select 'issue' as kind, id, name, state from sc_quality_issue where name='梁底钢筋保护层偏差' union all select 'standard', id, name, null as state from sc_check_standard where name='主体结构质量检查标准';"
run_check "safety plan risk and loop records exist" "s89_quality_safety_surface" \
  "select case when (select count(*) from sc_safety_plan where name='高支模专项安全施工方案' and state='approved') = 1 and (select count(*) from sc_safety_disclosure where name='高支模班前安全交底' and state='approved') = 1 and (select count(*) from sc_risk_library where name='项目安全风险库') = 1 and (select count(*) from sc_risk_item where name='高支模架体失稳') = 1 and (select count(*) from sc_hazard_source where name='1#楼高支模危险源' and state='controlled') = 1 and (select count(*) from sc_safety_issue where name='高支模剪刀撑局部缺失' and state='closed') = 1 and (select count(*) from sc_safety_patrol_task where name='高支模专项巡检' and state='done') = 1 then 'ok' else 'safety records missing' end;" \
  "select 'plan' as kind, id, name, state from sc_safety_plan where name='高支模专项安全施工方案' union all select 'hazard', id, name, state from sc_hazard_source where name='1#楼高支模危险源' union all select 'issue', id, name, state from sc_safety_issue where name='高支模剪刀撑局部缺失' union all select 'patrol', id, name, state from sc_safety_patrol_task where name='高支模专项巡检';"
run_check "site photo batches exist" "s89_quality_safety_surface" \
  "select case when count(*) = 2 then 'ok' else 'photo batches missing' end from sc_site_photo_batch where name in ('质量整改复验照片','安全整改复验照片');" \
  "select id, name, evidence_stage, quality_issue_id, safety_issue_id from sc_site_photo_batch where name in ('质量整改复验照片','安全整改复验照片') order by name;"
run_check "users exist" "s90_users_roles" \
  "select case when count(*) >= 6 then 'ok' else 'users missing' end from res_users where login in ('demo_pm','demo_finance','demo_cost','demo_audit','demo_readonly','svc_e2e_smoke');" \
  "select id, login, active from res_users where login in ('demo_pm','demo_finance','demo_cost','demo_audit','demo_readonly','svc_e2e_smoke') order by login;"
run_check "finance user lacks contract capability" "s90_users_roles" \
  "select case when count(*) = 0 then 'ok' else 'finance has contract group' end from res_groups_users_rel r where r.uid = (select id from res_users where login='demo_finance') and r.gid in (select id from res_groups where coalesce(name->>'zh_CN', name->>'en_US') like 'SC 能力 - 合同中心%');" \
  "select u.login, coalesce(g.name->>'zh_CN', g.name->>'en_US') as group_name from res_groups_users_rel r join res_users u on u.id = r.uid join res_groups g on g.id = r.gid where u.login='demo_finance' order by group_name;"
run_check "readonly user not in settlement user group" "s90_users_roles" \
  "select case when count(*) = 0 then 'ok' else 'readonly has settlement group' end from res_groups_users_rel r where r.uid = (select id from res_users where login='demo_readonly') and r.gid in (select id from res_groups where coalesce(name->>'zh_CN', name->>'en_US') = 'SC 能力 - 结算中心经办');" \
  "select u.login, coalesce(g.name->>'zh_CN', g.name->>'en_US') as group_name from res_groups_users_rel r join res_users u on u.id = r.uid join res_groups g on g.id = r.gid where u.login='demo_readonly' order by group_name;"
run_check "demo admin has full menu groups" "s90_users_roles" \
  "select case when (select count(*) from res_groups_users_rel r join ir_model_data d on d.res_id=r.gid and d.model='res.groups' where r.uid=(select id from res_users where login='sc_test_admin') and ((d.module='smart_core' and d.name='group_smart_core_admin') or (d.module='smart_construction_core' and d.name='group_sc_super_admin'))) = 2 then 'ok' else 'demo admin menu groups missing' end;" \
  "select u.login, d.module || '.' || d.name as group_xmlid, coalesce(g.name->>'zh_CN', g.name->>'en_US') as group_name from res_groups_users_rel r join res_users u on u.id=r.uid join res_groups g on g.id=r.gid join ir_model_data d on d.res_id=g.id and d.model='res.groups' where u.login='sc_test_admin' and d.module in ('smart_core','smart_construction_core') order by group_xmlid;"
if [ -z "$scenario" ] || [ "$scenario" = "s90_users_roles" ]; then
  printf '[demo.verify] S90 demo admin menu openability\n'
  if compose_dev exec -T odoo odoo shell -d "$DB_NAME" -c /var/lib/odoo/odoo.conf <<'PY'
import sys

admin = env.ref("smart_construction_demo.sc_demo_user_test_admin")
required_groups = [
    "smart_core.group_smart_core_admin",
    "smart_construction_core.group_sc_super_admin",
    "smart_construction_core.group_sc_cap_config_admin",
    "smart_construction_core.group_sc_cap_business_config_admin",
    "smart_construction_core.group_sc_cap_project_read",
    "smart_construction_core.group_sc_cap_cost_read",
    "smart_construction_core.group_sc_cap_material_read",
    "smart_construction_core.group_sc_cap_finance_read",
    "project.group_project_user",
    "project.group_project_manager",
]
missing_groups = [xmlid for xmlid in required_groups if not admin.has_group(xmlid)]
if missing_groups:
    print("missing demo admin groups:", ", ".join(missing_groups))
    sys.exit(1)

root = env.ref("smart_construction_core.menu_sc_root", raise_if_not_found=False)
domain = [("action", "!=", False)]
if root:
    domain.append(("id", "child_of", root.id))
menus = env["ir.ui.menu"].with_user(admin).search(domain)
failures = []
checked = 0
for menu in menus:
    action = menu.action if menu.action._name == "ir.actions.act_window" else False
    if not action or not action.res_model or action.res_model not in env:
        continue
    checked += 1
    model_name = action.res_model
    Model = env[model_name].with_user(admin)
    try:
        Model.check_access_rights("read", raise_exception=True)
        Model.search([], limit=1)
        if action.search_view_id:
            Model.with_context(load_all_views=True).get_view(
                view_id=action.search_view_id.id,
                view_type="search",
            )
        for mode in [m.strip() for m in (action.view_mode or "tree,form").split(",") if m.strip()][:3]:
            view_type = "tree" if mode == "list" else mode
            if view_type not in {"tree", "form", "kanban", "pivot", "graph", "calendar", "activity"}:
                continue
            view_id = False
            for action_view in action.view_ids:
                action_view_type = "tree" if action_view.view_mode == "list" else action_view.view_mode
                if action_view_type == view_type and action_view.view_id:
                    view_id = action_view.view_id.id
                    break
            if view_id:
                Model.with_context(load_all_views=True).get_view(view_id=view_id, view_type=view_type)
            else:
                Model.with_context(load_all_views=True).get_view(view_type=view_type)
    except Exception as exc:
        failures.append((menu.complete_name, model_name, type(exc).__name__, str(exc).splitlines()[0]))

if failures:
    print("demo admin menu open failures:", len(failures), "checked:", checked)
    for row in failures[:50]:
        print("FAIL", row)
    sys.exit(1)
print("ok demo admin menu openability checked:", checked)
PY
  then
    echo "✓ S90 demo admin can open delivered menus"
  else
    echo "✗ S90 demo admin can open delivered menus"
    exit 1
  fi
fi
run_check "showroom projects >= 8" "showroom" \
  "select case when count(*) >= 8 then 'ok' else 'showroom projects < 8' end from project_project p where $showroom_project_filter;" \
  "select p.id, p.name, p.lifecycle_state from project_project p where $showroom_project_filter order by p.id;"
run_check "showroom tasks >= 80" "showroom" \
  "select case when count(*) >= 80 then 'ok' else 'showroom tasks < 80' end from project_task t join project_project p on p.id = t.project_id where $showroom_project_filter;" \
  "select t.id, t.name, t.project_id from project_task t join project_project p on p.id = t.project_id where $showroom_project_filter order by t.id limit 20;"
run_check "showroom contracts >= 3" "showroom" \
  "select case when count(*) >= 3 then 'ok' else 'showroom contracts < 3' end from construction_contract c join project_project p on p.id = c.project_id where $showroom_project_filter;" \
  "select c.id, c.subject, c.project_id, c.state from construction_contract c join project_project p on p.id = c.project_id where $showroom_project_filter order by c.id;"
run_check "showroom stages >= 4" "showroom" \
  "select case when count(distinct p.stage_id) >= 4 then 'ok' else 'showroom stages < 4' end from project_project p where $showroom_project_filter;" \
  "select p.stage_id, count(*) from project_project p where $showroom_project_filter group by p.stage_id order by p.stage_id;"

run_check "showroom settlement projects in closing+" "showroom" \
  "select case when (select count(distinct p.id) from project_project p join sc_settlement_order s on s.project_id = p.id join ir_model_data d on d.res_id = p.stage_id and d.model='project.project.stage' and d.module='smart_construction_core' where $showroom_project_filter and d.name in ('project_stage_closing','project_stage_closed','project_stage_warranty','project_stage_archived')) >= 2 then 'ok' else 'showroom settlement stage coverage < 2' end;" \
  "select p.id, coalesce(p.name->>'zh_CN', p.name->>'en_US', p.name::text) as name, d.name as stage_xmlid from project_project p join sc_settlement_order s on s.project_id = p.id left join ir_model_data d on d.res_id = p.stage_id and d.model='project.project.stage' and d.module='smart_construction_core' where $showroom_project_filter order by p.id;"

echo "🎉 demo.verify PASSED"
