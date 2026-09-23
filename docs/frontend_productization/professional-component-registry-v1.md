# Professional Component Registry v1

## Authority

The registry is the single P0 frontend authority that decides whether a
Contract V2 `componentKey` may enter the production form renderer. Backend
`layoutContract.componentRegistry` remains transport metadata; it does not
declare frontend readiness.

Every registration declares:

- component key and semantic type;
- supported field types, presentation modes, and render profiles;
- required capabilities;
- renderer and explicit fallback;
- readiness: `ready`, `readable_fallback`, or `fail_closed`.

## Production chain

```text
decoded Contract V2 widget
→ normalized store
→ canonical Presenter
→ professional registry resolver
→ FormSection renderer
→ data-component-* semantic evidence
```

Resolution is fail closed. An unknown key, incompatible field type, unsupported
presentation mode or render profile, or missing capability raises a precise
invariant error before the field reaches the renderer. There is no generic or
silent component fallback.

`readable_fallback` is a registered, explicit state. In v1 it is reserved for
hierarchical collection data whose readable representation is supported while
its specialized professional interaction is not yet authoritative.

## Renderer contract

`renderer` and every `rendererByFieldType` value are members of one closed
union, `PROFESSIONAL_COMPONENT_RENDERERS`. A renderer name that no control
honours no longer compiles, so a registration can only point at a control the
production renderer actually draws. `FormSectionFieldSchema.componentRenderer`
is typed by the same union, so the consumer cannot widen it either.

`FORM_SECTION_TYPE_DIRECTED_RENDERER` (`FormSectionField`) is the deliberate
sentinel for "no professional control owns this field; the section's own
type-directed control renders it". It is named rather than implied, so a
drifted renderer is no longer indistinguishable from the sentinel once it
reaches the template. It is also the one union member that needs no branch of
its own.

`FormSection` fails closed on a renderer it does not know: the field renders a
visible, non-editable alert carrying `data-field-fail-closed` instead of a
silently editable input. The check runs before every other renderer branch,
because the branches that select a control from field type alone would
otherwise absorb a violation the registry should have caught.

`frontend_professional_component_registry_guard` holds both halves: the union
is closed and typed, and every union member other than the sentinel is
dispatched by a renderer branch. Dispatch is matched in its comparison form, in
one left-to-right pass that blanks comments and spans string, template and
regular expression literals, and only in a component's script, so a comment, a
quoted sentence, a pattern, or template text cannot stand in for a branch; the
branch surface is a glob, but a branch counts only for the element that renders
it: the comparison must sit in the body of a function named by a branch attribute
on a tag the script *imports*, or in the body of a function of an imported module
that such a body names, and it counts only for the renderer that element itself
is. The tag is read as the name Vue resolves, so a kebab-case tag counts as the
component it renders, and the template is read as an element tree: a branch counts only under
conditions that do not evaluate to a constant which renders nothing, only under the one
loop that renders the fields, and never on an element bound never to show. So neither a dead arrow in a sibling component,
nor a dead function in the section, nor a comparison parked in a helper that no
render element owns, nor a name only a dead duplicate carries can stand in for a
branch. A branch attribute may be quoted either way. Imports are
read from the code half alone with comments removed, so a commented line that
spells an import names nothing, and a renamed import is followed from the name it
binds to the name its module exports.
A pattern is recognised after a control statement as well as after an
operator, so `if (x) /.../ ` is a pattern rather than a division, while a doubled
operator (`hits++ / 2`) is a division rather than a pattern. The component is read
in two regions, and the regions are found by position rather than by a shortest
match: the markup half is the root template block, closed by nesting depth, so a
nested `<template>` does not end it early and a `<template>` written inside a
script literal is not the markup half; the code half is the concatenation of the
script blocks, and a script block that sits inside the markup half is not a code
half. Comments and attribute values are excluded while the blocks are located, so
a `<template>` or a `<script>` written inside either is not a block at all, and a
block without a closing tag is not one either. Inside the markup half only
comments are blanked and attribute values are kept, so `v-if="..."` and
`:data-...=` still match; inside the code half comments and literal contents are
both blanked, so an attribute quoted in the script disappears. A marker counts
only as an attribute *name*: a match that starts inside an attribute value, or
outside a tag, is text, not a binding, and a `<` opens a tag only when a closing
slash or a name follows it, so markup such as `<1 ...>` is text and cannot carry
one. The six semantic markers must be bound together on the element that iterates
the fields, on a `v-for` whose source carries a name rather than an empty
literal, and the fail-closed predicate call, its marker and a visible
`role="alert"` must be bound together on one element that the field list itself
loops over, with no `v-show`, `hidden` — written as an attribute whatever its
casing, or bound as `:hidden="flag"` with a value that can be truthy, in every
spelling Vue documents for that binding, modifiers included. A modifier is read
the way the browser reads it: `.attr` sets the attribute, and `hidden` is a
boolean attribute whose presence is the declaration, so `:hidden.attr="false"`
hides the tag even though `:hidden="false"` shows it — unless the value is the
constant `null` or `undefined`, bare or in parentheses (`:hidden.attr="(null)"`
is the same constant to Vue; an expression that only computes it, such as
`void 0`, is not resolved and still reads as hiding), which ask Vue to drop the
attribute, or empty,
which binds nothing at all. The attribute reading holds only as long as `.attr`
stands alone: `:hidden.prop.attr="false"` writes the property, so it shows the
tag. `.prop` and `.camel` set the property, so the value's truthiness decides
there and `:hidden.camel="false"` shows the tag, while a value written as a
string literal hides it however that string reads — `:hidden.camel="'false'"`,
the template literal `` `false` ``, and even `:hidden.camel="''"`, which Vue
writes onto a boolean attribute as present — and the value is read through
parentheses here as it is for `.attr`, so `:hidden="('')"` is that empty string
and `:hidden="(false)"` is still a constant that shows the tag — or hiding
`style` on it, and with no `v-bind` that hands it an attribute set the template
does not name (`v-bind="{ hidden: true }"`, `v-bind="attrs"`,
`v-bind:[name]="true"`, `v-bind.prop="{ hidden: true }"`). These readings are
taken from the alert's own tag *and from every element enclosing it*, because an
element that shows nothing hides the alert it contains: a `hidden` or a `v-bind`
on the field row hides the branch as surely as one on the branch itself does.
`:style.prop="…"` and `:style.attr="…"` hand their value straight to `el.style`
or to `setAttribute`, which coerce it to a string instead of merging it: an object
literal with no `toString` of its own becomes `[object Object]` and declares no
style, so `:style.prop="{ display: 'none' }"` declares none in a browser, while
an array is joined and a `toString` returns whatever that method says, so
`:style.prop="['display:none']"` and `:style.prop="{ toString() { return
'display:none' } }"` both reach the sheet. The guard does not re-run that
coercion: it reads a literal handed to a forced style as written, so the object
literal that a browser turns into `[object Object]` is refused too. That
over-rejection is deliberate and registered — the alternative is a substring
test for `toString`, which a computed key such as `{ ['toStr' + 'ing']: … }`
walks past. A value is read as the two readers read it. The compiler reads the
attribute value first, so an escape inside a literal spells its character and
`:style.prop="'display:\u006eone'"` is `display:none`, and a character
reference spells its character too — `:style="'display&#58;none'"` and
`:style="'display&#58none'"` are that same `display:none`, with
`&#x3A;`/`&#100;` spelling the colon and the letter the same way, while a name
the browser would leave as text is left as text here. The sheet reads the
declaration next, so a comment inside it is not part of it
(`:style="'display:/*x*/none'"` declares none), `opacity` hides at every
spelling of the number zero (`'opacity:.0'`, `'opacity:00'`) and `visibility`
hides at `collapse` as it does at `hidden`.
A *bound* value is an expression, and text an expression builds — joined
with `+`, written as a template literal, or produced by a call such as
`concat`, `replace`, `join` or `String.fromCharCode` — can spell a
declaration no single fragment spells, so the binding is refused rather than
followed: `:style.prop="['display' + ':none']"`,
`` :style.prop="`display:${'none'}`" ``,
`:style.prop="['display','none'].join(':')"` and
`:style.prop="'display'.concat(':none')"` each reach the sheet while no single
fragment of them spells the declaration. That reading is structural rather than
a list of the operator spellings seen so far: it is asked of the value with its
comments blanked and its literal contents blanked on top of them, and a call is
any `(` left there — so
`:style="'display'['concat'](':none')"` and
`:style="'display'/*c*/.concat/*b*/(':none')"` are calls, while neither a call
nor an operator written inside a string or a comment is one — and a `style=…`
that is markup rather than a binding keeps the text it wrote —
`style="width: calc(100% - 4px)"` declares nothing hiding. Only a value that
reads as a name, or as a member of one (`:style="rowStyle"`,
`:style="scope.row.cssText"`), is left to the reading above. The composition
reading is an over-rejection in the fail-closed direction on the same registered
footing: `:style="'color:' + 'red'"`, `:style="a + b"`, a call whose result
the source does not spell — `:style="tagColorStyle(option.color)"`,
`:style="rowStyle?.()"` — and a grouping parenthesis that calls nothing
(`:style="(rowStyle)"`, `:style="(a, b)"`), a regular expression literal
(`:style="/display:none/"`), declare no hiding style and are refused all the
same. What is *not* read is the CSS spelling of a property name or value
carried by a backslash escape (`:style="'display:\6e one'"`): the two readers
above resolve escapes the JavaScript way, not the CSS way, so that family stays
a registered limit rather than a reading.
Otherwise the hiding value is read from the bound `style` value rather than from the attribute text:
`:style="{ display: 'none' }"`, `:style="{ 'display': 'none' }"`,
`:style="{ ['display']: 'none' }"`, `style="Display: none"`, and the unquoted
`style=display:none` all compile to the declaration a browser reads, because a
declaration names its property the same way whether the name is bare, quoted, or
a computed key. A `style=…` that sits inside another attribute's *value* is that
value's text, so it is not a hiding declaration on the tag. A shape
parked under a condition that evaluates to a constant which renders nothing —
`true` renders, so it is not one of them — under another loop, or outside
the field list therefore cannot keep the contract green while the field falls
back silently. The
fail-closed half is checked
for binding, not presence: the marker must be bound with a `:` in the template,
the branch must call the predicate, the predicate must test membership in a set
that is a constant built from the closed union alone, named only by its
declaration and that test, and it must read the renderer as written, matching its
only producer. Rebinding an engine global the predicate reads fails, and that
rule reads the family rather than one spelling: reaching any name for the global
object — `globalThis`, `window`, `self`, `global`, and the browser's `frames`,
`parent`, `top`, and `opener`, read as identifiers rather than as property names
and read through an escape spelling, because `gl\u006FbalThis` is `globalThis` — a
declaration of `Boolean`, `Set` or one of their siblings, a reassignment of the
same name, an import that binds it, and *reading* `eval` or `Function` at all,
since `(0, eval)(...)` reaches the compiler without the call shape. The route to
the global is read as a family too: a constructor taken off a value,
`document.defaultView`, a dynamic `import(...)`, `Object.assign`, which puts a new
value behind a global name as an assignment does, a global name written as a
string key of any shape — quoted, templated, concatenated, or held in a name the
script binds to a string — and a timer *called* at all, since one handed a
string compiles it, are reported with it, because each reaches the same names by
another spelling. A key is read from every binding that can put a string behind
its name rather than from the last one the text holds: an initializer that
continues onto the next line, whether the operator joining the lines ends the
first or starts the second, an initializer that strips the type assertions
stacked after it (`'Boolean' as unknown as string`), a name a script appends to
with `+=` or with the `||=`, `&&=`, `??=` family, a name destructured out of a
value that spells a string — read as the name the pattern binds, so `{ k: key }`
counts as `key` — and a key that is a string the text does not spell out all
count, while a key whose every string lies outside the family above is left
alone. The brackets are read as an expression rather than as one spelling of a
key: the content may be wrapped in parentheses, carry `!`, `as`, `satisfies` or
an angle-bracket assertion, be joined by an operator (`(first ?? second)`,
`('con' + 'structor')`), and every name it reads is looked up among those
bindings, with nesting and each link of a chain (`value[first][second]`,
`value?.[first]?.[second]`) read as its own access. Reaching a builtin prototype in the script fails, and the family
is read rather than spelled: `.prototype`, `__proto__`, `setPrototypeOf` and
`getPrototypeOf`, `Reflect.set`/`defineProperty`/`deleteProperty`, and the
`Object.defineProperty`/`getOwnPropertyDescriptor` group, because that is how the
predicate would be disarmed after it is built. The union check covers the call sites as well as the union:
every registration must name a bare union member, no registration may sit outside
the closed list, the field-type mapping the factory builds is a renderer call
site too, and a renderer laundered through a cast fails. The semantic
`data-component-*` and `data-contract-*` markers are required in the same bound
form.
The base field type list is not restated here; the registry imports
`PROFESSIONAL_BASE_FIELD_TYPES`.

## Boundaries

- The registry does not grant data, model, record, action, or mutation rights.
- It does not infer `task` or `workspace`; it consumes the Presenter identity.
- It contains no model, action, menu, label, or industry-specific branches.
- It authorizes existing generic rendering capabilities; Phase 7 owns their
  professional component-family expansion.
- A registration is not a dynamic component loader. Its renderer name is an
  auditable authorization target for the current production renderer.
