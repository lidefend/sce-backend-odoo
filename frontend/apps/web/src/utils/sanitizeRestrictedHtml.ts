/**
 * 受限富文本（restricted_html canonical）只读渲染净化助手。
 *
 * 纵深防线（ADR-006 决策 3）：服务端 nh3 白名单是唯一净化权威，
 * 本助手仅在渲染前再收敛一次，防存储内容被旁路污染（如直连 DB 改写）
 * 进入应用外壳。标签与属性白名单与服务端 canonical 子集对齐：
 * 段落/标题/列表/粗斜体/受控表格子集/链接。
 */
const ALLOWED_TAGS = new Set([
  'a', 'b', 'br', 'em', 'h1', 'h2', 'h3', 'i', 'li', 'ol', 'p',
  'strong', 'table', 'tbody', 'td', 'th', 'thead', 'tr', 'ul',
]);

const DROP_WITH_CONTENT_TAGS = new Set(['iframe', 'object', 'script', 'style', 'svg']);

/** 受控属性白名单（colspan/rowspan 表格结构 / a 的 href 与 title） */
const ALLOWED_ATTRIBUTES: Record<string, Set<string>> = {
  a: new Set(['href', 'title']),
  td: new Set(['colspan', 'rowspan']),
  th: new Set(['colspan', 'rowspan']),
};

function safeLinkTarget(raw: string): string {
  const value = String(raw || '').trim();
  if (!value) return '';
  if (value.startsWith('/') || value.startsWith('#')) return value;
  try {
    const parsed = new URL(value, window.location.origin);
    return ['http:', 'https:', 'mailto:'].includes(parsed.protocol) ? value : '';
  } catch {
    return '';
  }
}

export function sanitizeRestrictedHtml(raw: unknown): string {
  if (typeof document === 'undefined') return '';
  const template = document.createElement('template');
  const source = String(raw ?? '');
  template.innerHTML = source;

  template.content.querySelectorAll('*').forEach((element) => {
    const tag = element.tagName.toLowerCase();
    if (DROP_WITH_CONTENT_TAGS.has(tag)) {
      element.remove();
      return;
    }
    if (!ALLOWED_TAGS.has(tag)) {
      element.replaceWith(...Array.from(element.childNodes));
      return;
    }

    const kept: Array<[string, string]> = [];
    Array.from(element.attributes).forEach((attribute) => {
      const name = attribute.name.toLowerCase();
      if ((ALLOWED_ATTRIBUTES[tag] || new Set<string>()).has(name)) {
        kept.push([attribute.name, attribute.value]);
      }
    });
    Array.from(element.attributes).forEach((attribute) => element.removeAttribute(attribute.name));
    if (tag === 'a') {
      const href = safeLinkTarget(
        kept.find(([name]) => name.toLowerCase() === 'href')?.[1] || '',
      );
      if (href) {
        element.setAttribute('href', href);
        element.setAttribute('rel', 'noopener noreferrer');
      }
      const title = kept.find(([name]) => name.toLowerCase() === 'title')?.[1];
      if (title) element.setAttribute('title', title);
    } else {
      kept.forEach(([name, value]) => {
        if (/^\d+$/.test(String(value).trim())) {
          element.setAttribute(name, String(Number(value.trim())));
        }
      });
    }
  });
  return template.innerHTML;
}
