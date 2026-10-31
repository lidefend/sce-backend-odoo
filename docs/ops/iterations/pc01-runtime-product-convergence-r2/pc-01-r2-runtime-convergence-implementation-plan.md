# PC-01 R2 统一整改实施设计（草案）

阶段：只读根因定位与整改设计，未改产品代码。

## 修复分层

1. 通用组件修复：`status_with_color` 状态映射补充 `to_define` 中性语义，显示“设定状态”。
2. 项目业务视图配置：身份摘要只突出一次项目编号与当前用户角色，责任信息保留四类字段。
3. 组件属性配置：mail 关注者/附件/时间线优先复用通用渲染器的折叠、列表/上传分离属性。
4. 字段帮助：核查四个 `data-field-help-trigger` 的实际 help 内容与交互，无有效帮助则收敛。
5. 暂不处理：A 轨合同业务边界、责任矩阵空态、三个 `NOT_VERIFIED`。

## 依据

- `pc-01-r2-status-component-root-cause.md`
- `pc-01-r2-project-collaboration-component-map.md`
- `pc-01-r2-identity-projection-map.json`
- `pc-01-r2-field-help-audit.json`
- `pc-01-r2-runtime-dom-acceptance.md`

## 验收

统一按 Business Page Productization Standard v1：L1 静态 → L2 定向 → L3 candidate 身份 →
L4 四视口 DOM → L5 Quick/CI/复审。
