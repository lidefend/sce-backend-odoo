-- Structural rollback only. Apply exclusively to the matching controlled database.
-- Value restoration for res_partner.x_custom_field requires the verified restricted archive.
ALTER TABLE "construction_contract_expense" ADD COLUMN "x_custom_field" date;
ALTER TABLE "construction_contract_income" ADD COLUMN "x_custom_field" character varying;
ALTER TABLE "construction_contract_income" ADD COLUMN "x_custom_field_2" double precision;
ALTER TABLE "construction_contract_income" ADD COLUMN "x_custom_field_3" character varying;
ALTER TABLE "construction_contract_income" ADD COLUMN "x_custom_field_4" character varying;
ALTER TABLE "construction_contract_income" ADD COLUMN "x_custom_field_5" date;
ALTER TABLE "project_project" ADD COLUMN "x_custom_field" date;
ALTER TABLE "res_partner" ADD COLUMN "x_custom_field" character varying;
ALTER TABLE "sc_general_contract" ADD COLUMN "x_custom_field" character varying;
ALTER TABLE "sc_general_contract" ADD COLUMN "x_custom_field_2" character varying;
ALTER TABLE "sc_general_contract" ADD COLUMN "x_custom_field_3" character varying;
