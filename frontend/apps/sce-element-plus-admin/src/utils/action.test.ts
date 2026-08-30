import { describe, expect, it } from "vitest";

import {
  groupRecordBusinessActions,
  isInlineBusinessAction,
  usesExecuteButtonIntent,
} from "./action";

describe("business action intent adapter", () => {
  const button = { name: "validate_tier", type: "object" };

  it.each(["execute", "button.execute", "execute_button", ""])(
    "routes %j through execute_button",
    (intent) => {
      expect(usesExecuteButtonIntent(intent, button)).toBe(true);
    },
  );

  it("does not rewrite explicit business intents", () => {
    expect(usesExecuteButtonIntent("payment.request.execute", button)).toBe(false);
  });

  it("does not treat an empty action descriptor as an executable button", () => {
    expect(usesExecuteButtonIntent("", {})).toBe(false);
  });

  it("requires an explicit inline presentation tier for embedded tabs", () => {
    const open = {
      key: "open_boq", label: "查看清单", type: "primary" as const,
      intent: "ui.contract", button: {}, params: {},
      target: { action_id: 88, model: "project.boq" },
    };
    const inline = {
      ...open,
      key: "open_boq_inline",
      presentationTier: "inline" as const,
    };
    const execute = {
      key: "generate", label: "生成任务", type: "primary" as const,
      intent: "execute", button, params: {}, presentationTier: "overflow" as const,
    };
    expect(isInlineBusinessAction(open)).toBe(false);
    expect(isInlineBusinessAction(inline)).toBe(true);
    expect(isInlineBusinessAction(execute)).toBe(false);
  });

  it("separates inline, command, overflow, and configuration actions", () => {
    const base = { type: "primary" as const, params: {}, button };
    const grouped = groupRecordBusinessActions([
      { ...base, key: "open", label: "查看清单", intent: "open", target: { action_id: 88 }, presentationTier: "inline" },
      { ...base, key: "approve", label: "审批通过", intent: "execute", presentationTier: "primary" },
      { ...base, key: "share", label: "分享", intent: "execute", presentationTier: "secondary" },
      { ...base, key: "validate", label: "校验", intent: "execute", presentationTier: "overflow" },
      { ...base, key: "settings", label: "表单设置", intent: "ui.local_mode", presentationTier: "configuration" },
    ]);
    expect(grouped.inline.map((action) => action.key)).toEqual(["open"]);
    expect(grouped.direct.map((action) => action.key)).toEqual(["approve", "share"]);
    expect(grouped.overflow.map((action) => action.key)).toEqual(["validate"]);
    expect(grouped.configuration.map((action) => action.key)).toEqual(["settings"]);
  });

  it("does not expose configuration actions to non-admin users", () => {
    const settings = {
      key: "settings", label: "表单设置", type: "primary" as const,
      intent: "ui.local_mode", button: {}, params: {}, presentationTier: "configuration" as const,
    };
    const grouped = groupRecordBusinessActions([settings], { isPlatformAdmin: false });
    expect(grouped.configuration).toEqual([]);
    expect(grouped.direct).toEqual([]);
    expect(grouped.overflow).toEqual([]);
  });
});
