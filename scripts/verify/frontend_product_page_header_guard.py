#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _read_makefile(path: str) -> str | None:
    """读取 Makefile 片段；不存在时返回 None（`-include` 与条件 include 都可能是可选的）。"""
    try:
        return (ROOT / path).read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError, PermissionError):
        return None


def _logical_lines(text: str) -> list[str]:
    r"""按 Make 的规则把行尾 `\` ＋换行拼成**逻辑行**（只用于指令级扫描，不用于 recipe 形状判定）。"""
    lines: list[str] = []
    buffer = ""
    for raw in text.splitlines():
        if raw.endswith("\\"):
            buffer += raw[:-1]
            continue
        lines.append(buffer + raw)
        buffer = ""
    if buffer:
        lines.append(buffer)
    return lines


def _unquote(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    return token


def _include_tokens(text: str) -> list[str]:
    r"""`include`／`-include`／`sinclude` 的**静态**路径 token。

    GNU make 有三个同义拼写（`include`、`-include`、`sinclude`），并且路径可以：
    用 `\` ＋换行续行、加引号、一行写多个。它们全是**静态可解析**的，若只认行首
    `-?include` ＋单物理行 ＋无引号，就等于给「在片段里重定义被守卫目标」留了整类拼写通道。
    含 `$(…)`／`${…}` 的动态 token 仍只能跳过（已在文档残限登记）。
    """
    tokens: list[str] = []
    for line in _logical_lines(text):
        match = re.match(r"^\s*(?:-|s)?include\s+(.+?)\s*$", line)
        if not match:
            continue
        for token in match.group(1).split("#")[0].split():
            if "$" in token:
                continue
            tokens.append(_unquote(token))
    return tokens


def _expand_include(token: str) -> list[str]:
    if any(char in token for char in "*?["):
        return sorted(str(path.relative_to(ROOT)) for path in ROOT.glob(token))
    return [token]


def _makefile_chain(root: str = "Makefile") -> dict[str, str]:
    """按 `include`／`-include` 展开 Makefile 链（跳过 `$(…)` 动态 token）。**只读仓库，不执行 make。**

    只看被守卫的那一个文件是不够的：Make 对同一目标取**最后一份 recipe**（并只给一条 warning），
    因此在被 include 的片段里重定义被守卫的目标就能整条替换断言里的 recipe，而原文件一字未动。
    动态 include（`include $(ENV_FILE_RESOLVED)`）与条件 include 无法静态展开，已在文档残限登记。
    """
    chain: dict[str, str] = {}
    pending = [root]
    while pending:
        path = pending.pop(0)
        if path in chain:
            continue
        text = _read_makefile(path)
        if text is None:
            continue
        chain[path] = text
        for token in _include_tokens(text):
            for target in _expand_include(token):
                if target not in chain:
                    pending.append(target)
    return chain


def _ignore_error_forms(chain: dict[str, str]) -> list[str]:
    """Make 级「失败不传播」通道：`.IGNORE` 特殊目标与 `MAKEFLAGS` 里的 `-i`／`--ignore-errors`。

    这两者都不改 recipe 的 shell 形状，却让整条（或全部）recipe 的失败不再让门禁失败。
    """
    failures: list[str] = []
    for path, text in chain.items():
        for line in _logical_lines(text):
            if re.match(r"^\.IGNORE\s*:", line):
                failures.append(
                    "header entry contract test wiring loses failure propagation "
                    f"({path} declares the .IGNORE special target: a failing step stops failing the gate)"
                )
            # `override`／`export` 前缀与 `\` 续行不改变语义：`override MAKEFLAGS += -i`
            # 与 `MAKEFLAGS += \<换行>-i` 都能给整棵 make 加上 `-i`。
            match = re.match(
                r"^\s*(?:override\s+|export\s+|unexport\s+)*(?:GNU)?MAKEFLAGS\s*[:+?]?=\s*(.*)$", line
            )
            if not match:
                continue
            value = match.group(1).split("#")[0]
            for token in value.replace("(", " ").replace(")", " ").split():
                letters = token[1:] if token.startswith("-") and not token.startswith("--") else ""
                if token == "--ignore-errors" or (letters and "i" in letters):
                    failures.append(
                        "header entry contract test wiring loses failure propagation "
                        f"({path} sets MAKEFLAGS {token}: a failing step stops failing the gate)"
                    )
                    break
    return failures


def _failure_propagation_overrides(chain: dict[str, str]) -> list[str]:
    """另外两条不改 recipe 字面内容、却能让失败不传播的 Make 级通道。

    - `.ONESHELL:`：整条 recipe 交给**一个** shell 执行，Make 只看**最后一行**的退出码，
      于是在 recipe 尾部补一行 `@true` 就能让前面的失败不再让门禁失败；
    - `SHELL`／`.SHELLFLAGS` 被**重定义**：把 `SHELL` 指到恒返回 0 的程序（如 `/bin/true`）
      或让 `.SHELLFLAGS` 丢掉 `-e`，同样让步骤失败不传播。因此与「被守卫目标只定义一次」同口径：
      这两者跨 include 链**最多只能定义一次**（重定义即要求显式登记）。
    """
    failures: list[str] = []
    assignments: dict[str, list[str]] = {}
    for path, text in chain.items():
        for line in _logical_lines(text):
            if re.match(r"^\.ONESHELL\s*:", line):
                failures.append(
                    "header entry contract test wiring loses failure propagation "
                    f"({path} enables .ONESHELL: only the last recipe line's status is observed, "
                    "so a trailing no-op can hide a failing step)"
                )
            match = re.match(r"^\s*(?:override\s+|export\s+|unexport\s+)*(SHELL|\.SHELLFLAGS)\s*[:?+]?=", line)
            if match:
                assignments.setdefault(match.group(1), []).append(path)
    for name, paths in sorted(assignments.items()):
        if len(paths) > 1:
            failures.append(
                "header entry contract test wiring loses failure propagation "
                f"({name} is redefined across the include chain in {len(paths)} places "
                f"[{', '.join(sorted(set(paths)))}]: a fragment can silently change recipe failure semantics)"
            )
    return failures


def _non_literal_targets(chain: dict[str, str]) -> list[str]:
    """`$(VAR):` 这类**非字面量目标名**可以在被 include 的片段里顶掉被守卫目标。

    目标名是变量展开时，静态侧看不到它到底展开成什么，因此按失败关闭方向处理：
    链上任何一条非字面量目标定义都要求显式登记（本仓库当前为零）。
    """
    failures: list[str] = []
    for path, text in chain.items():
        for line in _logical_lines(text):
            if not line or line.startswith("\t") or line.lstrip().startswith("#"):
                continue
            match = re.match(r"^([^:=\t#]+):(?!=)", line)
            if match and "$" in match.group(1):
                failures.append(
                    "header entry contract test wiring cannot be checked statically "
                    f"({path} defines a non-literal target '{match.group(1).strip()}': "
                    "a variable target can silently redefine the guarded recipe)"
                )
    return failures


def _ignored_recipe_prefix(line: str) -> bool:
    """Make 的 `-` 前缀（`@-`／`-@` 等前缀字符集里含 `-`）让该步骤的失败被忽略。"""
    return "-" in re.match(r"^[@+\-\s]*", line).group(0)


def _matches_recipe(line: str, program: str, args: tuple[str, ...]) -> bool:
    """判定 recipe 行是否**真的**按预期形状执行 `program`。

    任何「子串存在性」判定都有伪命令通道，至少四类：
    `@echo <整条命令行>` 只是回显；`@node --version # <文件名>` 把文件名塞进注释；
    `@node --version; echo <文件名>` 用 shell 分隔符把真程序与文件名拆到两段；
    `@node --version <文件名>`／`@python3 -c "pass" unittest <文件名>` 让首 token 与文件名同时在场，
    但程序根本不执行该文件。

    因此这里要求：**先摘掉 shell 重定向**（`2>&1`／`>/dev/null` 不是链式分隔符），再按
    `;`／`&&`／`||`／`|`／`&` 切段——必须**恰好只剩一段**（**不丢弃空段**，否则尾随 `&` 的后台化
    会伪装成「只有一段」），且该段「首 token 就是该程序」并且
    「其后紧跟的前 `len(args)` 个 token 与预期参数**逐个相等且同序**」。
    比「参数集合包含」强：参数被换位、被替换成 `--version`／`-c` 之类的空转开关都会失败。

    「恰好一段」是必需的而不是洁癖：`false && <step>`／`true || <step>` 让步骤**永不执行**，
    而 `<step> || true`／`<step> ; true`／`<step> &` 让步骤执行但**失败不再传播**（`&` 后台化后
    shell 立刻以 0 退出），三者都能让门禁形同虚设。重定向的剥离必须**不吞分隔符**：
    `>/dev/null||true`（分隔符紧跟重定向、无空白）与 `>/dev/null; echo x` 同样必须失败。
    代价是 `|| true` 这类「真实步骤的尾部修饰」也会失败——按失败关闭方向处理，并在文档残限中登记。

    另有一条 Make 级通道与 shell 形状无关：recipe 行的 **`-` 前缀**（`@-esbuild …`／`-@node …`）让
    Make 忽略该步骤的退出码，「失败不传播」而 shell 形状完全正常。因此前缀字符集里出现 `-` 一律失败；
    `.IGNORE` 特殊目标与 `MAKEFLAGS` 里的 `-i`／`--ignore-errors` 由 `_ignore_error_forms` 单独判定。
    """
    prefix = re.match(r"^[@+\-\s]*", line).group(0)
    if _ignored_recipe_prefix(line):
        return False
    body = line[len(prefix):].split("#")[0]
    body = re.sub(r"\d*>&\s*\d+", " ", body)
    body = re.sub(r"\d*>>?\s*[^\s;|&]+", " ", body)
    segments = re.split(r"&&|\|\||[;|&]", body)
    if len(segments) != 1:
        return False
    tokens = segments[0].split()
    if not tokens or not re.search(rf"(^|/){re.escape(program)}$", tokens[0]):
        return False
    if len(tokens) < len(args) + 1:
        return False
    return all(tokens[1 + offset] == expected for offset, expected in enumerate(args))


def _code_view(text: str, mask_strings: bool) -> str:
    """按**标记模式**生成「只剩真实代码」的视图（长度与原文一致、下标对齐）。

    模式：模板正文／标签内部／`<script>`・`<style>` 原始段／`<textarea>`・`<title>`（RCDATA），
    以及模板 `{{ }}` 插值。
    - 正文里的裸撇号（`<p>owner's</p>`）不得打开引号状态，否则其后的 `<!-- -->` 会被当成实现（假失败）；
    - 正文里的 `<!--` 只在**插值之外**才是注释，`{{ '<!--' }}` 里的字符是数据不是注释——
      否则它就是又一条「在字符串里写一段注释符把真实代码夹掉」的静默通道；
    - `textarea`／`title` 是 **RCDATA**：其中的 `<!--` 是**文本**而不是注释；否则
      `<textarea><!--</textarea>` 会把其后**真实渲染**的整段模板吞成注释（真实调用点对门禁隐身）；
    - 标签内部与 `{{ }}` 内**引号感知**：`'https://…'` 里的 `//` 不会被误当成注释；
    - 行注释与块注释只在脚本语义里成立：模板正文里的斜杠是文本，把整行 `//` 一律当注释
      会让「同一行里 `//` 之后的真实标签／绑定」被静默夹掉；
    - `mask_strings` 为真时字符串与模板字面量的**内容**被掩码（字面量里的实现不是实现）。
    """
    out = list(text)
    index = 0
    quote = None
    mode = "text"
    interpolation = 0
    raw_tag = False
    rcdata = False
    length = len(text)

    def blank(from_at: int, to_at: int) -> None:
        for at in range(from_at, min(to_at, length)):
            if out[at] != "\n":
                out[at] = " "

    while index < length:
        char = text[index]
        if quote is not None:
            if char == "\\" and index + 1 < length:
                if mask_strings:
                    out[index] = "\u0001"
                    out[index + 1] = "\u0001"
                index += 2
                continue
            if char == quote:
                quote = None
            elif mask_strings:
                out[index] = "\u0001"
            index += 1
            continue
        if mode == "tag":
            if char in "\"'`":
                quote = char
                index += 1
                continue
            if char == ">":
                mode = "script" if raw_tag else "text"
                raw_tag = False
                index += 1
                continue
            index += 1
            continue
        if mode == "text" and interpolation == 0 and rcdata:
            if re.match(r"</(?:textarea|title)\b", text[index:], re.IGNORECASE):
                rcdata = False
                mode = "tag"
                index += 1
                continue
            if text.startswith("{{", index):
                interpolation = 1
                index += 2
                continue
            index += 1
            continue
        if mode == "text" and interpolation == 0:
            if text.startswith("<!--", index):
                end = text.find("-->", index + 4)
                stop = length if end == -1 else end + 3
                blank(index, stop)
                index = stop
                continue
            if text.startswith("{{", index):
                interpolation = 1
                index += 2
                continue
            if char == "<":
                raw_tag = re.match(r"<(?:script|style)\b", text[index:], re.IGNORECASE) is not None
                rcdata = re.match(r"<(?:textarea|title)\b", text[index:], re.IGNORECASE) is not None
                mode = "tag"
                index += 1
                continue
            index += 1
            continue
        if interpolation > 0:
            if text.startswith("{{", index):
                interpolation += 1
                index += 2
                continue
            if text.startswith("}}", index):
                interpolation -= 1
                index += 2
                continue
        elif re.match(r"</(?:script|style)\b", text[index:], re.IGNORECASE):
            mode = "tag"
            index += 1
            continue
        if char in "\"'`":
            quote = char
            index += 1
            continue
        if char == "/" and text.startswith("/*", index):
            end = text.find("*/", index + 2)
            stop = length if end == -1 else end + 2
        elif char == "/" and text.startswith("//", index) and (index == 0 or text[index - 1] != ":"):
            end = text.find("\n", index)
            stop = length if end == -1 else end
        else:
            index += 1
            continue
        blank(index, stop)
        index = stop
    return "".join(out)


def _strip_comments(text: str) -> str:
    """注释清零、字面量原样：模板属性值里的 `$attrs` 这类「结构标记」只能在这个视图里读。"""
    return _code_view(text, False)


def _code_only(text: str) -> str:
    """注释清零、字面量内容掩码：判断「实现是否存在」只能用这个视图，字面量诱饵不算实现。"""
    return _code_view(text, True)


def _active_recipe_lines(makefile: str, target: str) -> list[str]:
    """返回 `target` 目标下**未被注释掉**的 recipe 行。

    只做子串存在性检查会让「注释掉烘焙／执行行、保留文件名」这种静默摘除逃过门禁，
    因此这里必须按 Makefile 结构取目标块，并剔除以 `#` 开头的 recipe 行。

    Make 会把**以 `\\` 结尾的物理行**与下一行拼成一条逻辑行后再交给同一个 shell；逐物理行判定
    会让 `\\t@node x.mjs \\` ＋ `\\t|| true` 这类续行修饰对门禁不可见（shell 实际执行 `node x.mjs || true`，
    失败被吞掉而守卫仍 PASS）。因此这里先按 Make 的规则拼逻辑行，再剔除整条逻辑行的 `#` 注释行。
    """
    physical: list[str] = []
    inside = False
    for line in makefile.splitlines():
        if re.match(rf"^{re.escape(target)}\s*:", line):
            inside = True
            continue
        if not inside:
            continue
        if line.startswith("\t"):
            physical.append(line.strip())
            continue
        if not line.strip():
            continue
        break
    logical: list[str] = []
    buffer = ""
    for body in physical:
        if body.endswith("\\"):
            buffer += body[:-1] + " "
            continue
        logical.append((buffer + body).strip())
        buffer = ""
    if buffer.strip():
        logical.append(buffer.strip())
    return [line for line in logical if line and not line.startswith("#")]


def validate() -> list[str]:
    failures: list[str] = []
    component = source("frontend/apps/web/src/components/product-page-header/ProductPageHeader.vue")
    model = source("frontend/apps/web/src/app/presentation/productPageHeader.ts")
    required_component = [
        "data-product-page-header", "data-presentation-mode", "data-render-profile",
        "data-dirty-state", "data-header-variant", "data-workspace-action-bar",
        ":class=\"{ 'sc-visually-hidden': hideTitle }\"", "data-title-visibility",
        "product-page-header--title-hidden", "product-page-header__status:empty",
    ]
    required_model = [
        "title", "subtitle", "breadcrumb", "presentationMode", "renderProfile", "dirtyState",
        "statusbar", "primaryAction", "overflowActions", "exitAction",
        "PRODUCT_PAGE_HEADER_PRIMARY_ACTION_MULTIPLE", "PRODUCT_PAGE_HEADER_READONLY_SAVE_FORBIDDEN",
    ]
    for marker in required_component:
        if marker not in component:
            failures.append(f"ProductPageHeader missing {marker}")
    for marker in required_model:
        if marker not in model:
            failures.append(f"header model missing {marker}")
    for adapter in (
        "frontend/apps/web/src/components/design-system/ScPageHeader.vue",
        "frontend/apps/web/src/components/page/PageHeader.vue",
        "frontend/apps/web/src/components/template/PageHeader.vue",
    ):
        if "ProductPageHeader" not in source(adapter):
            failures.append(f"header adapter bypasses ProductPageHeader: {adapter}")
    registry = source("frontend/apps/web/src/app/presentation/productPageHeaderAdapters.ts")
    fixed_mode_adapters = {
        "components/page/PageHeader.vue": "page",
        "components/design-system/ScPageHeader.vue": "design-system",
    }
    # 判据分两个视图，避免「合法文案／无关命名」被误伤（假失败）：
    # ① 具名符号（`$attrs`／`attrs`／`useAttrs`）只在**字面量内容已掩码**的视图里判；
    # ② 模板属性 `v-bind="…attrs…"` 的取值是真代码（不在①的视图里），因此在未掩码视图上单独判。
    attrs_symbol = re.compile(r"\buseAttrs\b|\battrs\b")
    # `v-bind.prop=`／`v-bind.camel=`／`v-bind.attr=` 与 `v-bind=` 是同一个「整对象展开」通道
    # （编译器都输出 `_guardReactiveProps(_ctx.attrs)`），修饰符不得让判据失明。
    attrs_binding = re.compile(r"v-bind(?:\.[\w-]+)*\s*=\s*[\"'][^\"']*attrs", re.IGNORECASE)

    def attrs_fallback(text: str) -> bool:
        return bool(attrs_symbol.search(_code_only(text)) or attrs_binding.search(_strip_comments(text)))

    if attrs_fallback(component):
        failures.append(
            "ProductPageHeader must not forward unregistered axes through $attrs/useAttrs()/attrs"
        )
    for adapter_path, entry_id in fixed_mode_adapters.items():
        adapter_raw = source(f"frontend/apps/web/src/{adapter_path}")
        if attrs_fallback(adapter_raw):
            failures.append(
                f"header adapter must not forward unregistered axes through $attrs/useAttrs()/attrs: {adapter_path}"
            )
        adapter_source = _strip_comments(adapter_raw)
        if re.search(r"(?<![:\w-])presentation-mode=\"", adapter_source):
            failures.append(f"header adapter hardcodes presentation mode instead of the entry registry: {adapter_path}")
        if re.search(r":presentation-mode=\"\s*['\"]", adapter_source):
            failures.append(f"header adapter binds presentation mode to a literal: {adapter_path}")
        binding = re.search(r":presentation-mode=\"([A-Za-z_$][\w$]*)\"", adapter_source)
        if binding is None:
            failures.append(
                f"header adapter does not single-source its fixed presentation mode (no identifier binding): {adapter_path}"
            )
        elif not re.search(
            rf"const\s+{re.escape(binding.group(1))}\s*=\s*resolveProductPageHeaderFixedMode\(\s*['\"]{entry_id}['\"]\s*\)",
            adapter_source,
        ):
            failures.append(
                "header adapter does not single-source its fixed presentation mode "
                f"(constant {binding.group(1)} must come from resolveProductPageHeaderFixedMode('{entry_id}')): {adapter_path}"
            )
        if f"'{adapter_path}'" not in registry:
            failures.append(f"header entry registry misses adapter path: {adapter_path}")
    for entry_path in (
        "components/template/PageHeader.vue",
        "pages/contractForm/ContractFormProductHeader.vue",
    ):
        if f"'{entry_path}'" not in registry:
            failures.append(f"header entry registry misses entry path: {entry_path}")
    if "PRODUCT_PAGE_HEADER_DIRECT_CONSUMERS" not in registry or "PRODUCT_PAGE_HEADER_AXES" not in registry:
        failures.append("header entry registry does not declare axes and direct consumers")
    contract_test = "frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts"
    if not (ROOT / contract_test).exists():
        failures.append("header entry contract test is missing")
    makefile_chain = _makefile_chain()
    failures.extend(_ignore_error_forms(makefile_chain))
    failures.extend(_failure_propagation_overrides(makefile_chain))
    failures.extend(_non_literal_targets(makefile_chain))
    wired_target = "verify.frontend.product_page_header.unit"
    definition_files = [
        path
        for path, text in makefile_chain.items()
        for line in text.splitlines()
        if re.match(rf"^{re.escape(wired_target)}\s*:", line)
    ]
    if len(definition_files) != 1:
        failures.append(
            "header entry contract test is not wired into verify.frontend.product_page_header.unit "
            f"(target must be defined exactly once across the include chain, found {len(definition_files)}: "
            "a later duplicate target — including one introduced through `include` — overrides the guarded recipe)"
        )
    recipe = (
        _active_recipe_lines(makefile_chain[definition_files[0]], wired_target)
        if len(definition_files) == 1
        else []
    )
    if any(_ignored_recipe_prefix(line) for line in recipe):
        failures.append(
            "header entry contract test wiring loses failure propagation "
            "(a guarded recipe line uses Make's `-` ignore-error prefix: the step can fail without failing the gate)"
        )
    # 三条接线必须按**预期形状**真实执行：程序 ＋ 紧跟其后的预期参数（同序、逐个相等）。
    if not any(
        _matches_recipe(
            line,
            "esbuild",
            (
                "frontend/apps/web/scripts/product_page_header_adapter_contract_test.ts",
                "--bundle",
                "--platform=node",
                "--format=esm",
            ),
        )
        for line in recipe
    ):
        failures.append(
            "header entry contract test is not wired into verify.frontend.product_page_header.unit "
            "(esbuild bundle step missing or disabled)"
        )
    if not any(_matches_recipe(line, "node", ("/tmp/product-page-header-adapter-contract-test.mjs",)) for line in recipe):
        failures.append(
            "header entry contract test is not wired into verify.frontend.product_page_header.unit "
            "(node execution step missing or disabled)"
        )
    if not any(
        _matches_recipe(line, "python3", ("-m", "unittest", "scripts/verify/test_frontend_product_page_header_guard.py"))
        for line in recipe
    ) or not any(
        _matches_recipe(line, "python3", ("scripts/verify/frontend_product_page_header_guard.py",)) for line in recipe
    ):
        failures.append(
            "header entry contract test is not wired into verify.frontend.product_page_header.unit "
            "(guard unit test or guard script step missing or disabled)"
        )
    # 门禁挂点本身也要防摘除：把 unit 目标从 quick／release 门禁的前置里删掉，比改 recipe 更隐蔽。
    for gate_target in ("verify.frontend.quick.gate", "verify.frontend.release.unit"):
        # 必须按**前置 token** 比对而不是子串：把 unit 目标从真实前置里删掉、只留在行尾 `#` 注释里，
        # 子串判定仍会 PASS（`#` 在前置行里就是注释）；同一目标的多处定义也要一并计入。
        # 前置在 Make 里是**可累加**的：同目标的多次定义合并前置，因此要按 include 链的全集收集。
        gate_prerequisites: set[str] = set()
        for text in makefile_chain.values():
            for line in text.splitlines():
                if not re.match(rf"^{re.escape(gate_target)}\s*:", line):
                    continue
                gate_prerequisites.update(line.split(":", 1)[1].split("#")[0].split())
        if wired_target not in gate_prerequisites:
            failures.append(
                "header entry contract test is not wired into verify.frontend.product_page_header.unit "
                f"({gate_target} no longer depends on it: the gate hook itself can be silently detached)"
            )
    contract = source("frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue")
    for marker in (':presentation-mode="presentationMode"', ':render-profile="mode"', ':dirty-state="headerDirtyState"'):
        if marker not in contract:
            failures.append(f"contract header misses formal axis {marker}")
    for marker in ('canonicalActionEvidenceAttributes(action)', "'data-action-method'", "'data-action-enabled'", "'data-action-allowed'"):
        if marker not in contract:
            failures.append(f"canonical header action misses evidence marker {marker}")
    for marker in ('form-header-mobile-actions', 'mobileActionAuthority', 'mobilePresentedDirectActions', 'aria-label="更多页面操作"', ':data-mobile-action-count', ':data-mobile-action-keys'):
        if marker not in contract:
            failures.append(f"contract header mobile action settlement misses {marker}")
    if 'v-if="headerOverflowItems.length && !isNarrowViewport"' not in contract:
        failures.append("contract header desktop overflow must be structurally excluded on narrow viewports")
    if 'v-if="headerOverflowItems.length" class="form-header-more-actions"' in contract:
        failures.append("contract header must not rely on CSS to hide a parallel desktop overflow control")
    if "...(mobileActionAuthority.value.keys.includes('back:form.back') ? [{ value: 'builtin:back', label: props.backLabel" not in contract:
        failures.append("contract header mobile action settlement can hide the only exit action")
    if 'role="menu"' in contract or 'role="menuitem"' in contract:
        failures.append("contract header disclosure must preserve native button semantics")
    action_view = source("frontend/apps/web/src/views/ActionView.vue")
    if "<ProductPageHeader" not in action_view or '<h1 class="sc-visually-hidden">{{ vm.page.title }}</h1>' in action_view:
        failures.append("ActionView does not delegate collection/scene identity to ProductPageHeader")
    contract_page = source("frontend/apps/web/src/pages/ContractFormPage.vue")
    contract_page_style = source("frontend/apps/web/src/pages/contractForm/ContractFormPage.css")
    if '<h1 v-if="initialFormLoading"' not in contract_page:
        failures.append("ContractForm loading identity may duplicate the stable page header h1")
    for marker in ('actions-in-header', '@canonical-save="saveRecord()"', ':status-interactive="!isConfigurationPreview && nativeStatusbar.visible && !nativeStatusbar.readonly"'):
        if marker not in contract_page:
            failures.append(f"ContractForm does not project direct edit actions into header: {marker}")
    if ":deep(.template-page-header" in contract_page_style:
        failures.append("ContractForm page must not patch shared header internals through deep selectors")
    for stale_selector in ("template-page-header-main", "template-page-header-status", "template-page-header-actions"):
        if stale_selector in contract_page_style:
            failures.append(f"ContractForm page retains stale header DOM selector: {stale_selector}")
    for marker in ("position: sticky", "data-has-status", "product-page-header__actions"):
        if marker not in component:
            failures.append(f"ProductPageHeader does not own shared internal header layout: {marker}")
    for marker in (
        "font-size:var(--sc-product-text-title)",
        "font-weight:var(--sc-pattern-page-header-title-weight)",
        "line-height:32px",
    ):
        if marker not in component:
            failures.append(f"ProductPageHeader does not consume semantic title typography: {marker}")
    if "font-size:22px" in component or "font-weight:700" in component:
        failures.append("ProductPageHeader restores detached title typography literals")
    if ".product-page-header__identity{flex:0 1 auto;min-width:0}" not in component:
        failures.append("ProductPageHeader mobile identity retains a desktop flex basis")
    if ".product-page-header__status{flex:0 1 auto;width:100%" not in component:
        failures.append("ProductPageHeader mobile status retains a desktop flex basis as vertical height")
    for marker in ("flex-wrap: wrap", "container-name:page-header-status", "container-type:inline-size"):
        if marker not in component:
            failures.append(f"ProductPageHeader status layout does not respond to available container space: {marker}")
    if "@media(max-width:1500px){.product-page-header--task[data-has-status='true']" in component:
        failures.append("ProductPageHeader status layout must not use a widened viewport breakpoint as a container proxy")
    canonical_actions = source("frontend/apps/web/src/pages/contractForm/contractFormHeaderCanonicalActions.ts")
    for marker in ("input.floorplan?.decisionMode", "input.floorplan.directActions", "input.floorplan.overflowActions", "['primary', 'secondary'].includes(action.tier)", "['overflow', 'configuration'].includes(action.tier)"):
        if marker not in canonical_actions:
            failures.append(f"canonical header action floorplan rendering misses {marker}")
    if "localSavePrimary" in canonical_actions or "authorizedLocalSave" in canonical_actions:
        failures.append("canonical header actions must not invent local save orchestration")
    driver = source("frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue")
    for marker in ('showProductActions && !actionsInHeader',):
        if marker not in driver:
            failures.append(f"DriverHost still owns a parallel action bar: {marker}")
    if driver.count(':visible-actions="visibleActions"') != 2:
        failures.append("canonical task and workspace native surfaces do not share visible action projection")
    if "action.actionRef.actionId === 'form.save' && action.enabled" not in driver:
        failures.append("DriverHost local save is not bound to authorized canonical form.save")
    if "props.renderModel?.identity.mode === 'create' || props.dirty" in driver:
        failures.append("DriverHost edit save must not wait for dirty state")
    nested_heading_paths = (
        "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue",
        "frontend/packages/ui/src/components/SceneHierarchySurface.vue",
        "frontend/packages/ui/src/components/SceneCollectionSurface.vue",
        "frontend/packages/ui/src/components/SceneObjectPage.vue",
    )
    for nested in nested_heading_paths:
        if "<h1" in source(nested):
            failures.append(f"nested renderer competes with ProductPageHeader h1: {nested}")
    native_renderer = source("frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue")
    canonical_presenter = source("frontend/apps/web/src/app/presentation/contractFormPresenter.ts")
    canonical_bridge = source("frontend/apps/web/src/pages/contractForm/canonicalNativeFormBridge.ts")
    canonical_driver = source("frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue")
    if "/\\/header(?:\\[|\\/|$)/.test(nativeLocator)" not in canonical_presenter:
        failures.append("native form-header actions are not projected into the product header action channel")
    if "claimedStatusbarNodeIdentity && canonicalNodeIdentity === claimedStatusbarNodeIdentity" not in canonical_bridge:
        failures.append("canonical body statusbar de-duplication is not bound to the exact header-claimed node")
    if "text(node.widget || attrs.widget).toLowerCase() === 'statusbar'" in canonical_bridge:
        failures.append("canonical body still hides every statusbar instead of the exact header claim")
    if ':claimed-statusbar-node-identity="nativeStatusbarNodeIdentity"' not in contract_page:
        failures.append("ContractForm does not pass the exact claimed statusbar node into the body bridge")
    for marker in ('v-if="!preserveAuthoritativeBusinessSections"', '<CanonicalNativeFormSurface\n        v-else'):
        if marker not in canonical_driver:
            failures.append(f"canonical driver does not preserve authoritative business sections: {marker}")
    if ':authoritative-business-section-mode="nativeBridge.authoritativeBusinessSectionMode"' in canonical_driver:
        failures.append("canonical driver restores stale per-renderer business-section projection")

    component_tokens = source("frontend/packages/design-tokens/tokens/component.json")
    product_patterns = source("frontend/apps/web/src/styles/product-patterns.css")
    tdesign_theme = source("frontend/packages/ui/src/kits/tdesign/theme.css")
    form_section = source("frontend/apps/web/src/components/template/FormSection.vue")
    typography_markers = (
        (component_tokens, '"font_size": "{font.size_md}"', "input body-size token"),
        (product_patterns, ".sc-form-label {", "shared form label rule"),
        (product_patterns, "font-size: var(--sc-product-text-sm);", "shared supporting-text token"),
        (tdesign_theme, "--td-font-size-body-medium: var(--sc-product-text-body);", "TDesign body-size bridge"),
        (tdesign_theme, "--td-font-size-body-small: var(--sc-product-text-sm);", "TDesign supporting-size bridge"),
        (form_section, ".label {\n  font-size: var(--sc-product-text-sm);", "native field label token"),
        (
            form_section,
            ".readonly-value {\n  box-sizing: border-box;\n  display: grid;\n  align-items: center;\n  width: 100%;\n  max-width: 100%;\n  min-width: 0;\n  font-size: var(--sc-product-text-body);",
            "native readonly body token and shrinkable slot",
        ),
    )
    for text, marker, label in typography_markers:
        if marker not in text:
            failures.append(f"shared typography mapping misses {label}: {marker}")
    if 'v-bind="nativeActionEvidenceAttributes' not in native_renderer:
        failures.append("native action controls must expose canonical action evidence attributes")
    for marker in ("data-action-key", "data-action-ref", "data-backend-identity"):
        if marker not in native_renderer:
            failures.append(f"native action evidence is missing {marker}")
    for marker in ("line-break: strict", "text-wrap: balance", "font-size: 24px"):
        if marker not in native_renderer:
            failures.append(f"native record title responsive treatment is missing {marker}")
    app_shell = source("frontend/apps/web/src/layouts/AppShell.vue")
    router = source("frontend/apps/web/src/router/index.ts")
    for page_route in ("home", "scene-home", "my-work", "scene-my-work", "api-key-management", "action", "record", "model-form", "not-found"):
        route_declaration = next(
            (line for line in router.splitlines() if f"name: '{page_route}'" in line),
            "",
        )
        if "pageHeadingOwner: 'content'" not in route_declaration:
            failures.append(f"page-header route does not declare content heading authority: {page_route}")
    for view in ("frontend/apps/web/src/views/HomeView.vue", "frontend/apps/web/src/views/MyWorkView.vue"):
        view_source = source(view)
        for marker in ("<ProductPageHeader", "usePageIdentityRuntime"):
            if marker not in view_source:
                failures.append(f"workspace page does not consume content heading authority: {view}: {marker}")
    for marker in ("contentOwnsPageHeading", "route.meta?.pageHeadingOwner === 'content'", "!contentOwnsPageHeading.value"):
        if marker not in app_shell:
            failures.append(f"AppShell does not consume route heading authority: {marker}")
    if "formDesignerKeepsHeadline" in app_shell or "BUSINESS_CONFIG_MODES.lowCode" in app_shell:
        failures.append("AppShell must not override content heading authority for low-code form routes")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_product_page_header_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_product_page_header_guard] PASS adapters=3")
