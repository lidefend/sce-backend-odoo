# F1 根因核查

**根因未知，待核实、暂不修复。** Linux未复现持续错位不否定Windows人工观察。用户已暂停排查，不再补充实验。

## 源码事实

以运行时声明SHA `3f46dd7eba9f351386fee446151ee9eb545d56a4` 为参照；文件blob及与main一致性见 [source-identity.json](source-identity.json)。

- `frontend/apps/web/src/components/template/formSection.mapper.ts:195,251` 解析helpText；`FormSection.vue:41–44,155–158,413` 用ScPopover和click触发声明生成帮助入口，aria-controls关联内容。
- `components/design-system/ScPopover.vue:2–16,45–61` 桥接TDesignPopup，默认bottom/click、destroy-on-close；visible-change仅同步ref。没有显式attach、popperOptions或滚动关闭策略。
- `tdesignPrimitiveBridge.ts` → `frontend/packages/ui/src/primitives.ts:45` → TDesign Popup；包版本1.20.5，Popper2.11.8。
- 本地锁定依赖 `tdesign-vue-next/es/popup/props.mjs` 默认attach body；container.mjs经Teleport挂载。运行时测得popup position:absolute、transform定位，不支持直接断言position:fixed根因。
- popup.mjs:175–194,373–392在document捕获mousedown，点击触发器/弹层之外时关闭；204–208卸载销毁Popper、定时器和监听；281–316更新位置时检查触发器脱离DOM或零宽高。普通离开视口不等于零宽高。
- Popper eventListeners.js默认监听reference/popper滚动父容器和window resize，调用update。源码解释了稳定后跟随的机制，不证明Windows实际事件链。
- NativeFormTreeRenderer.vue:88–98页签lazy=false/destroy-on-hide=false，面板v-show；864–875生成data-section-tab。运行时页签是经营概况、描述、设置等，不存在任务描述的计划与责任选择器。

依赖分析基于本地已安装的锁定版本，未独立重建已部署bundle，不能只凭版本宣称二进制一致。

## 运行时事实与解释边界

详细结果见 [复现记录](f1-reproduction.md) 与 [测量索引](f1-measurements.json)。真实外部点击关闭符合现有依赖实现；离开视口但expanded仍true、不可见符合没有显式scroll-close的实现。这里只确认实现行为，不替产品负责人定义期望。

直接scrollTop后即时采样曾比稳定结果落后140px；推断可能涉及异步更新时序，但缺少对应绘制帧和Windows事件证据，不能认定共同根因。连续真实滚轮72帧没有持续分离。38px是内容偏移，popup根节点偏移30px，不能混用坐标口径。

已复现的持续错位缺陷：无。人工观察差异：保留。SPA、Windows缩放、人工具体入口和纯组件隐藏/卸载路径：未充分验证。页签关闭和完整文档导航成功不能代替这些结论。
