/**
 * 数据域 tab 纯函数（G7.3）：工作表按 tab 切换服务端 domain（如清单「已发布/编制中」版本状态）。
 * 刻意零运行时 import（type-only），保持 node 单测可 esbuild 直跑（不拖 api/client 链）。
 */
export type WorksheetDomainTab = { key: string; label: string; domain: unknown[] };
export type WorksheetDomainTabSource = { domain?: unknown; domain_tabs?: unknown };

/** 规范化数据域 tab：config 未下发 domain_tabs 时返回空数组，工作表行为与旧契约一致 */
export function resolveWorksheetDomainTabs(sheet: WorksheetDomainTabSource): WorksheetDomainTab[] {
  const tabs = Array.isArray(sheet.domain_tabs) ? sheet.domain_tabs : [];
  const seen = new Set<string>();
  const output: WorksheetDomainTab[] = [];
  tabs.forEach((tab) => {
    if (!tab || typeof tab !== 'object') return;
    const key = String((tab as { key?: unknown }).key || '').trim();
    if (!key || seen.has(key)) return;
    seen.add(key);
    const domain = (tab as { domain?: unknown }).domain;
    output.push({
      key,
      label: String((tab as { label?: unknown }).label || key).trim(),
      domain: Array.isArray(domain) ? domain : [],
    });
  });
  return output;
}

/** 按 tab key 合成有效 sheet domain：key 无效时返回原 domain（默认兜底，不变异原数组） */
export function applyWorksheetDomainTab<T extends WorksheetDomainTabSource>(sheet: T, tabKey: string): T {
  const tab = resolveWorksheetDomainTabs(sheet).find((item) => item.key === tabKey);
  return tab ? { ...sheet, domain: tab.domain } : sheet;
}
