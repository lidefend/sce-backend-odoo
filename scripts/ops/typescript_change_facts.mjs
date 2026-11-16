#!/usr/bin/env node
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(HERE, '../..')
const TS_PATH =
  process.env.SCE_TYPESCRIPT_PATH ||
  path.join(ROOT, 'frontend/apps/web/node_modules/typescript/lib/typescript.js')

const loaded = await import(pathToFileURL(TS_PATH).href)
const ts = loaded.default || loaded

function scriptViews(filename, text) {
  if (!filename.endsWith('.vue')) return [{ text, lineOffset: 0 }]
  const views = []
  const pattern = /<script\b[^>]*>([\s\S]*?)<\/script>/gi
  let match
  while ((match = pattern.exec(text))) {
    const prefix = text.slice(0, match.index + match[0].indexOf('>') + 1)
    views.push({
      text: match[1],
      lineOffset: (prefix.match(/\n/g) || []).length,
    })
  }
  return views
}

function scriptKind(filename) {
  if (filename.endsWith('.tsx')) return ts.ScriptKind.TSX
  if (filename.endsWith('.jsx')) return ts.ScriptKind.JSX
  if (filename.endsWith('.js') || filename.endsWith('.mjs') || filename.endsWith('.cjs')) return ts.ScriptKind.JS
  return ts.ScriptKind.TS
}

function nodeName(node) {
  if (node.name && ts.isIdentifier(node.name)) return node.name.text
  if (node.name && ts.isStringLiteral(node.name)) return node.name.text
  return ''
}

function importBinding(node) {
  const specifier = ts.isStringLiteral(node.moduleSpecifier) ? node.moduleSpecifier.text : ''
  const bindings = []
  const clause = node.importClause
  if (clause?.name) bindings.push({ imported: 'default', local: clause.name.text })
  const named = clause?.namedBindings
  if (named && ts.isNamespaceImport(named)) {
    bindings.push({ imported: '*', local: named.name.text })
  } else if (named && ts.isNamedImports(named)) {
    for (const element of named.elements) {
      bindings.push({
        imported: element.propertyName?.text || element.name.text,
        local: element.name.text,
      })
    }
  }
  return {
    specifier,
    type_only: Boolean(clause?.isTypeOnly),
    bindings,
  }
}

function callName(node) {
  if (!ts.isCallExpression(node)) return ''
  const expression = node.expression
  if (ts.isIdentifier(expression)) return expression.text
  if (ts.isPropertyAccessExpression(expression)) return expression.name.text
  return ''
}

function visit(node, symbols, fields, imports, importBindings, assertions, state) {
  let kind = ''
  if (ts.isFunctionDeclaration(node)) kind = 'function'
  else if (ts.isClassDeclaration(node)) kind = 'class'
  else if (ts.isInterfaceDeclaration(node)) kind = 'interface'
  else if (ts.isTypeAliasDeclaration(node)) kind = 'type'
  else if (ts.isEnumDeclaration(node)) kind = 'enum'
  else if (ts.isVariableStatement(node)) kind = 'variable'
  else if (ts.isMethodDeclaration(node) || ts.isMethodSignature(node)) kind = 'method'
  else if (ts.isPropertyDeclaration(node) || ts.isPropertySignature(node) || ts.isPropertyAssignment(node)) kind = 'field'
  else if (ts.isImportDeclaration(node)) {
    const moduleName = ts.isStringLiteral(node.moduleSpecifier) ? node.moduleSpecifier.text : ''
    imports.add(moduleName)
    importBindings.push(importBinding(node))
  } else if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) {
    if (!node.arguments.length || !ts.isStringLiteral(node.arguments[0])) {
      state.dynamic_dependency_possible = true
    }
  }

  const assertedCall = callName(node)
  if (
    assertedCall
    && [
      'assert',
      'equal',
      'notEqual',
      'deepEqual',
      'strictEqual',
      'deepStrictEqual',
      'throws',
      'match',
      'ok',
      'expect',
      'test',
      'it',
    ].includes(assertedCall)
  ) {
    assertions.push({
      call: assertedCall,
      line: state.source.getLineAndCharacterOfPosition(node.getStart()).line + 1 + state.lineOffset,
    })
  }

  if (kind === 'variable' && ts.isVariableStatement(node)) {
    for (const declaration of node.declarationList.declarations) {
      const name = ts.isIdentifier(declaration.name) ? declaration.name.text : ''
      if (name) {
        const start = declaration.getStart(state.source)
        const end = declaration.getEnd()
        symbols.push({
          name,
          kind,
          start_line: state.source.getLineAndCharacterOfPosition(start).line + 1 + state.lineOffset,
          end_line: state.source.getLineAndCharacterOfPosition(end).line + 1 + state.lineOffset,
        })
      }
    }
  } else if (kind && kind !== 'field') {
    const name = nodeName(node)
    if (name) {
      const start = node.getStart(state.source)
      const end = node.getEnd()
      symbols.push({
        name,
        kind,
        start_line: state.source.getLineAndCharacterOfPosition(start).line + 1 + state.lineOffset,
        end_line: state.source.getLineAndCharacterOfPosition(end).line + 1 + state.lineOffset,
      })
    }
  } else if (kind === 'field') {
    const name = nodeName(node)
    if (name) fields.add(name)
  }
  ts.forEachChild(node, child =>
    visit(child, symbols, fields, imports, importBindings, assertions, state)
  )
}

function facts(filename, text) {
  const symbols = []
  const fields = new Set()
  const imports = new Set()
  const importBindings = []
  const assertions = []
  let dynamicDependencyPossible = false
  for (const view of scriptViews(filename, text)) {
    const source = ts.createSourceFile(
      filename,
      view.text,
      ts.ScriptTarget.Latest,
      true,
      scriptKind(filename),
    )
    const state = {
      source,
      lineOffset: view.lineOffset,
      dynamic_dependency_possible: false,
    }
    visit(source, symbols, fields, imports, importBindings, assertions, state)
    dynamicDependencyPossible ||= state.dynamic_dependency_possible
  }
  const unique = new Map()
  for (const symbol of symbols) {
    const key = `${symbol.kind}:${symbol.name}:${symbol.start_line}:${symbol.end_line}`
    unique.set(key, symbol)
  }
  return {
    ok: true,
    symbols: [...unique.values()].sort((a, b) =>
      a.start_line - b.start_line || a.name.localeCompare(b.name)
    ),
    fields: [...fields].sort(),
    imports: [...imports].filter(Boolean).sort(),
    import_bindings: importBindings,
    assertion_calls: assertions,
    dynamic_dependency_possible: dynamicDependencyPossible,
  }
}

let input = ''
for await (const chunk of process.stdin) input += chunk
const payload = JSON.parse(input || '{}')
const output = {}
for (const file of payload.files || []) {
  try {
    output[file.path] = {
      before: facts(file.path, file.before || ''),
      after: facts(file.path, file.after || ''),
    }
  } catch (error) {
    output[file.path] = {
      ok: false,
      error: String(error instanceof Error ? error.message : error),
    }
  }
}
process.stdout.write(JSON.stringify(output))
