# G4 Theme/Mobile 增量收口 — 审计报告与交付记录

> 阶段：G4（进入条件：G1 基线稳定 ✅）。
> 验收口径：**无第二套页面、token 或数据契约**。
> 定位：证据化审计收口（仿 G2 模式），不新建 Theme Engine、不重建移动工程。
> 基线 SHA：`089f20e3`（G3.3-A 合流后 main）。

## 1. 审计范围与方法

对 theme/mobile 两个轨道 A 专题，以冻结基线 SHA 执行静态审计：

- 守卫执行（fail-closed）：`design_token_system.py`、`frontend_theme_profile_guard.py`、`frontend_collection_mobile_record_row_guard.py`
- 全仓 grep：token 前缀族、断点/设备契约下发、独立移动页面、直用桥接变量
- 契约面检查：`presentation_hints` / `surface_mapping` 的前后端出现位置与语义

## 2. G4.1 Theme/Token 审计结论

### 2.1 证据

| 检查项 | 结论 | 证据 |
| --- | --- | --- |
| Token 单一真相源 | ✅ 唯一 | `frontend/packages/design-tokens`（token-authority.json 声明 primitive/semantic/component/pattern 四层 + `allowedConsumerScope` 消费边界） |
| Token 系统守卫 | ✅ PASS | `[design_token_system] PASS phase0_variable_classification=131`；brand literal、裸 z-index、primitive 直引、legacy 分类边界全过 |
| 主题 profile 守卫 | ✅ PASS | `[theme_profile_guard] PASS profiles=3 declared=3 brand/radius=consistent orthogonality=ok`（profile 与 light/dark 正交，高对比例外受控） |
| 主题运行时 | ✅ 单一 | `src/styles/theme.ts`：light/dark/system + 3 profile，localStorage 仅存个人偏好，`main.ts` 引导 |
| 第二 token 体系 | ✅ 无 | `.vue` 中零 `var(--td-` 直用；tdesign 仅经 `tdesign-bridge.css` 桥接层 |
| 后端主题契约 | ✅ 无越界 | 后端不下发主题配置；品牌/覆盖属 P2/P3 决策待办 |

### 2.2 保持 SUPERSEDED / ADR-PENDING 的事项（不实施）

按总控计划 §18 决策待办，以下未决前不得进入生产实现，本轮**零代码**：

- Theme 可覆盖 Token allowlist、品牌资产 carrier、P2/P3 覆盖顺序
- `ui.theme` capability 边界（品牌名/Logo/token 覆盖的校验与回退契约）

## 3. G4.2 Mobile/响应式审计结论

### 3.1 证据

| 检查项 | 结论 | 证据 |
| --- | --- | --- |
| 后端断点/设备契约 | ✅ 零下发 | grep `addons/` 无 `"xs"/"md"/"lg"/breakpoint` emission；`contract_governance_surface_mapping.py` 为契约治理快照对比（native vs governed），非设备 surface 映射 |
| 单一 renderer | ✅ | 无独立移动路由/页面；响应式为纯 CSS media queries 于同一组件树 |
| 列表移动形态 | ✅ 守卫覆盖 | `frontend_collection_mobile_record_row_guard.py`：ListPage 恰一个共享移动行适配器，legacy 内联呈现零残留 |
| safe-area 处理 | ⚠️ 部分失效 → 已修复 | AppShell.css / ObjectTaskPage.vue 共 3 处 `env(safe-area-inset-*)`，但 viewport meta 缺 `viewport-fit=cover`（R-G4-01） |
| `presentation_hints` | ⬜ ADR-PENDING | 前后端均未实现（零引用），符合"正式 Schema 为决策待办"；后端未越界先行 |

### 3.2 债务盘点（记录不修）

- **断点碎片化**：max-width 值共 14 种（760×22、640×11、900×9、860×9、960×8、520×7、720×5、920×3、768×3、560×3、480×3、600×2、680×2、390×2）。按 mobile.md「冻结 SHA 基线、只处理证据化差距」记为 Phase 0 债务；统一断点属大重构，须单独立项（且受「超级组件拆分期」约束）。
- **局部溢出/信息优先级漂移**：需五视口视觉验证（依赖运行环境），与 G3.3-B 同批执行。

## 4. G4 交付物

| 交付物 | 说明 |
| --- | --- |
| `frontend/apps/web/index.html` | R-G4-01 修复：viewport meta 补 `viewport-fit=cover`，激活 3 处 safe-area 处理 |
| `scripts/verify/frontend_mobile_viewport_guard.py` | 新守卫：viewport meta 必含 `width=device-width`/`initial-scale=1`/`viewport-fit=cover`；禁 `user-scalable=no`/`maximum-scale=1`（可访问性底线）；safe-area 使用与 cover 声明交叉一致性校验 |
| `scripts/verify/test_frontend_mobile_viewport_guard.py` | 守卫 unittest 7 例 |
| `make/frontend.mk` | 注册 `verify.frontend.mobile_viewport.unit`，挂入 `verify.frontend.pr.unit` 与 `verify.frontend.release.unit` 聚合链 |
| 本文档 | 审计证据与结论 |

## 5. 验收对照

| 总控验收项 | 状态 |
| --- | --- |
| 无第二套页面 | ✅ 审计证据 §3.1 |
| 无第二套 token | ✅ 审计证据 §2.1 |
| 无第二套数据契约 | ✅ 后端零设备/断点契约下发，`presentation_hints` 保持 ADR-PENDING 未先行 |

## 6. 后续

- G3.3-B 与 Mobile 五视口验收同批执行（需环境）
- 断点统一与 `presentation_hints` Schema 各自走独立 ADR/立项
- G5（新能力 ADR：Chart/Gantt/Excel/PDF/Editor）进入条件为 G3 结论——挂接已完成，验收待环境；按计划推进 ADR 起草
