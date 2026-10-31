# 76 · Project Detail Legacy Consumer Compatibility（PC-009）

## 结论

PC-009 = NOT_VERIFIED（两个入口一致）

## 已识别消费链（SOURCE_STATIC）

- `app/contracts/v2/client.ts`：`loadContractV2` → `ui.contract.v2` intent。
- `app/contracts/v2/store.ts`：`createContractV2Store`。
- `pages/contractForm/useRecordFormFieldSchemas.ts`：`formFields` /
  `layoutNodes` 消费。
- `components/template/NativeFormTreeRenderer.vue`：containerTree 消费。
- `pages/ContractFormPage.vue`：`structureAuthority === 'container_tree'` 分支
  选择 native 快照。

## 缺口

1. 未运行旧消费者回归测试（PC-009 需要 TEST_EXECUTION +
   `old_consumer_regression` coverage）。
2. 新增 `fieldOwnership` / `pageComposition` / containerTree 对旧消费者的影响
   未通过实际执行验证。
3. 两个 Action/View 是否发生结构串用未证明。

## 证据

机器可读：`evidence-bundle-project-590.json` / `evidence-bundle-project-652.json`
（PC-009 两条 SOURCE_STATIC 证据：v2/client.ts、NativeFormTreeRenderer.vue）。
源码级证据已 VERIFIED，但不足以判定兼容性 PASS。
