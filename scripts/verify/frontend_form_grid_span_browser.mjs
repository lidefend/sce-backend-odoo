#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { launchChromium } from './playwright_runtime.mjs';

const ROOT = process.cwd();
const PHASE = process.env.FE_PRO_04WR3_PHASE || 'final';
const OUTPUT_ROOT = path.join(ROOT, 'artifacts/frontend-professional/fe-pro-04wr3');
const OUTPUT = path.join(OUTPUT_ROOT, PHASE);
const REPORT = path.join(OUTPUT_ROOT, `${PHASE}-report.json`);
const FORM_SECTION = path.join(ROOT, 'frontend/apps/web/src/components/template/FormSection.vue');
const CANONICAL_RENDERER = path.join(
  ROOT,
  'frontend/apps/web/src/pages/contractForm/CanonicalFormNodeRenderer.vue',
);
// The canonical node grid arranges a container's direct children on the same
// 24-track grid the field grid uses, so one declared span places a node and a
// field identically.
const CANONICAL_GRID_UNITS = 24;
// The canonical children used by the behaviour matrix: a whole-row node, a
// half node, a quarter node, and a mixed set whose declared spans disagree -
// the mixed set is the case a column-count grid cannot present (it would place
// all three at one column of the declared count, i.e. the same width).
const CANONICAL_SPAN_SETS = [[24], [12], [6], [24, 12, 12], [12, 12, 12]];
// Container inline sizes chosen clear of the declared folds (479 / 959).
const CANONICAL_CONTAINER_WIDTHS = [420, 700, 1200];
// Container inline sizes chosen clear of the two declared folds (479 / 959), so a
// measured container is always on the face the expectation names.
const CONTAINER_WIDTHS = [420, 700, 1200];
const COLUMNS = [1, 2, 3];
const DECLARED_SPANS = [6, 8, 12, 16, 24];
const GRID_UNITS = 24;
// Declared tracks share the grid with the column gap, so the rendered width ratio
// sits slightly below the bare track ratio; the band is a proportion, not a class.
// The gap effect at these container widths stays under 0.019, so the geometric
// check is secondary to the exact resolved track count and stays tight enough not
// to accept an off-by-one track.
const WIDTH_TOLERANCE = 0.03;

function check(value, message) {
  if (!value) throw new Error(message);
}

function productionStyle() {
  const source = fs.readFileSync(FORM_SECTION, 'utf8');
  const match = source.match(/<style scoped>([\s\S]*?)<\/style>/);
  check(match, 'FormSection scoped style not found');
  return match[1];
}

// The declared faces: one column below 480, two up to 959, and above that the
// 24-unit desktop grid the contract projects a declared span onto.
function canonicalRendererStyle() {
  const source = fs.readFileSync(CANONICAL_RENDERER, 'utf8');
  const match = source.match(/<style scoped>([\s\S]*?)<\/style>/);
  check(match, 'CanonicalFormNodeRenderer scoped style not found');
  return match[1];
}

// The behaviour the canonical node grid must present, derived from the declared
// span and the declared fold alone: on the desktop face the child takes its
// declared span out of the 24-unit grid, on the two-track folded face the
// declared band gives it one of the two tracks or the whole row, and below the
// single width one track owns the row.  The fold redefines the track count
// because 24 tracks carry 23 column gaps, so a folded face that kept them would
// give the narrowest container no track at all.  A compact readonly fact grid
// keeps its declared tracks at every width.  ``full`` means the whole row.
function canonicalGridFace(containerWidth, declaredSpan, readonlyFact) {
  if (containerWidth >= 960) return { tracks: CANONICAL_GRID_UNITS, span: declaredSpan, gap: null };
  // A compact readonly fact grid keeps the declared two-track face instead of
  // taking the one-track fold. It cannot keep the declared 24 tracks either:
  // those carry 23 declared column gaps that no folded container can fit, so
  // the face it holds is the declared medium one, with the declared band.
  if (!readonlyFact && containerWidth < 480) return { tracks: 1, span: 'full', gap: 0 };
  return declaredSpan > CANONICAL_GRID_UNITS / 2
    ? { tracks: 2, span: 'full', gap: null }
    : { tracks: 2, span: 1, gap: null };
}

function canonicalFixtureMarkup(containerWidth, declaredSpans, readonlyFact) {
  const children = declaredSpans.map((span, index) => (
    `<div id="node-${index}" class="canonical-form-node canonical-form-node--field"`
    + ` data-contract-span="${span}" data-contract-band="${declaredBand(span)}"`
    + ` style="--canonical-node-grid-span: ${span}">span ${span}</div>`
  )).join('\n      ');
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    :root { --sc-app-border: #cbd5e1; --sc-app-text-primary: #0f172a; --sc-app-focus-ring: #93c5fd; }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 24px 0 24px 24px; font: 14px sans-serif; color: #0f172a; background: #f8fafc; }
    .fixture { width: ${containerWidth}px; max-width: 100%; background: white; }
    .canonical-form-node { min-height: 48px; padding: 8px; background: #eff6ff; border: 1px solid #93c5fd; }
    ${canonicalRendererStyle()}
  </style></head><body>
    <div class="fixture">
      <section id="container" class="canonical-form-node canonical-form-node--container${readonlyFact ? ' canonical-form-node--readonly-fact' : ''}">
      <div class="canonical-form-node-children">
      ${children}
      </div>
      </section>
    </div>
  </body></html>`;
}

async function measureCanonical(page, declaredSpans, containerWidth, readonlyFact = false) {
  await page.setViewportSize({ width: Math.max(390, containerWidth + 96), height: 340 });
  await page.setContent(canonicalFixtureMarkup(containerWidth, declaredSpans, readonlyFact), {
    waitUntil: 'domcontentloaded',
  });
  return page.evaluate(({ spans, gridUnits }) => {
    // The node is the query container and the grid is a child of it, exactly as
    // the field grid does it: a container query cannot style the query container
    // itself, so the grid that owns the fold must be the child.
    const container = document.querySelector('#container');
    const grid = container.querySelector(':scope > .canonical-form-node-children');
    const gridStyle = getComputedStyle(grid);
    const gridRect = grid.getBoundingClientRect();
    const gap = parseFloat(gridStyle.columnGap) || 0;
    const resolvedTracks = gridStyle.gridTemplateColumns.match(/-?\d+(?:\.\d+)?px/g) || [];
    // The container query and the declared tracks both measure the content box.
    const contentWidth = grid.clientWidth - parseFloat(gridStyle.paddingLeft) - parseFloat(gridStyle.paddingRight);
    const trackCount = resolvedTracks.length || 1;
    const track = (contentWidth - (trackCount - 1) * gap) / trackCount;
    const children = spans.map((span, index) => {
      const element = document.querySelector(`#node-${index}`);
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      const rowSpan = /^span\s+(\d+)/.exec(String(style.gridColumnStart || ''));
      const ownsRow = String(style.gridColumnStart || '') === '1' && String(style.gridColumnEnd || '') === '-1';
      return {
        declared_span: span,
        grid_column_start: style.gridColumnStart,
        grid_column_end: style.gridColumnEnd,
        rendered_span: ownsRow ? 'full' : (rowSpan ? Number(rowSpan[1]) : null),
        width: Number(rect.width.toFixed(2)),
        overflow_right: Number(Math.max(0, rect.right - gridRect.right).toFixed(2)),
      };
    });
    return {
      container_width: Number(gridRect.width.toFixed(2)),
      content_width: Number(contentWidth.toFixed(2)),
      computed_grid_template_columns: gridStyle.gridTemplateColumns,
      computed_track_count: trackCount,
      track: Number(track.toFixed(4)),
      column_gap: gap,
      children,
    };
  }, { spans: declaredSpans, gridUnits: CANONICAL_GRID_UNITS });
}

function expectedTrackCount(containerWidth) {
  if (containerWidth < 480) return 1;
  if (containerWidth < 960) return 2;
  return GRID_UNITS;
}

// The band the renderer publishes for the medium fold: a declared span past half
// the grid owns the whole row, anything narrower is half of the two-track face.
function declaredBand(span) {
  return span > GRID_UNITS / 2 ? 'full' : 'half';
}

function expectedSpanTracks(declaredSpan, containerWidth) {
  const tracks = expectedTrackCount(containerWidth);
  if (tracks === GRID_UNITS) return declaredSpan;
  if (tracks === 1) return 1;
  return declaredBand(declaredSpan) === 'full' ? 2 : 1;
}

function fixtureMarkup(columns, span, containerWidth) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    :root { --sc-app-border: #cbd5e1; --sc-app-text-primary: #0f172a; --sc-app-focus-ring: #93c5fd; }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 24px 0 24px 24px; font: 14px sans-serif; color: #0f172a; background: #f8fafc; }
    .fixture { width: ${containerWidth}px; max-width: 100%; background: white; }
    .field { min-height: 64px; padding: 12px; background: #eff6ff; border: 1px solid #93c5fd; }
    ${productionStyle()}
  </style></head><body>
    <div class="fixture">
      <section id="section" class="template-form-section">
        <div id="grid" class="template-form-section-grid template-form-section-grid--columns-${columns}">
          <div id="field" class="field" data-field-span="${span}" data-field-band="${declaredBand(span)}">${columns} column contract / span ${span}</div>
        </div>
      </section>
    </div>
  </body></html>`;
}

async function measure(page, columns, span, containerWidth) {
  await page.setViewportSize({ width: Math.max(390, containerWidth + 96), height: 240 });
  await page.setContent(fixtureMarkup(columns, span, containerWidth), { waitUntil: 'domcontentloaded' });
  return page.evaluate(({ declaredColumns, declaredSpan, targetWidth }) => {
    const section = document.querySelector('#section');
    const grid = document.querySelector('#grid');
    const field = document.querySelector('#field');
    const sectionStyle = getComputedStyle(section);
    const gridStyle = getComputedStyle(grid);
    const fieldStyle = getComputedStyle(field);
    const gridRect = grid.getBoundingClientRect();
    const fieldRect = field.getBoundingClientRect();
    const resolvedTracks = gridStyle.gridTemplateColumns.match(/-?\d+(?:\.\d+)?px/g) || [];
    const spanned = /span\s+(\d+)/.exec(String(fieldStyle.gridColumnStart || ''));
    return {
      declared_columns: declaredColumns,
      declared_span: declaredSpan,
      target_container_width: targetWidth,
      container_width: Number(
        (section.clientWidth - parseFloat(sectionStyle.paddingLeft) - parseFloat(sectionStyle.paddingRight)).toFixed(2),
      ),
      computed_grid_template_columns: gridStyle.gridTemplateColumns,
      computed_track_count: resolvedTracks.length,
      first_track_width: Number((parseFloat(resolvedTracks[0]) || 0).toFixed(2)),
      field_grid_column_start: fieldStyle.gridColumnStart,
      field_grid_column_end: fieldStyle.gridColumnEnd,
      rendered_span: spanned ? Number(spanned[1]) : (String(fieldStyle.gridColumnEnd || '') === '-1' ? 'full' : null),
      field_width: Number(fieldRect.width.toFixed(2)),
      grid_width: Number(gridRect.width.toFixed(2)),
      overflow: Number(Math.max(0, fieldRect.right - gridRect.right, grid.scrollWidth - grid.clientWidth).toFixed(2)),
    };
  }, { declaredColumns: columns, declaredSpan: span, targetWidth: containerWidth });
}

async function captureFixture(page, style, entry) {
  await page.setViewportSize(entry.viewport);
  await page.setContent(fixtureMarkup(entry.columns, entry.span, entry.container), { waitUntil: 'domcontentloaded' });
  const screenshot = path.join(OUTPUT, `${entry.key}.png`);
  await page.screenshot({ path: screenshot, fullPage: true });
  return { ...entry, screenshot: path.relative(ROOT, screenshot), production_style_sha: style.length };
}

async function main() {
  fs.mkdirSync(OUTPUT, { recursive: true });
  const style = productionStyle();
  const browser = await launchChromium({ headless: true });
  try {
    const page = await browser.newPage();
    const matrix = [];
    for (const containerWidth of CONTAINER_WIDTHS) {
      for (const columns of COLUMNS) {
        for (const span of DECLARED_SPANS) {
          const row = await measure(page, columns, span, containerWidth);
          row.declared_track_count = expectedTrackCount(row.container_width);
          row.expected_span_tracks = expectedSpanTracks(row.declared_span, row.container_width);
          row.expected_width_ratio = Number((row.expected_span_tracks / row.declared_track_count).toFixed(4));
          row.rendered_width_ratio = Number((row.field_width / row.grid_width).toFixed(4));
          row.width_delta = Number(Math.abs(row.rendered_width_ratio - row.expected_width_ratio).toFixed(4));
          row.implicit_track_count = Math.max(0, row.computed_track_count - row.declared_track_count);
          row.rendered_span_tracks = row.rendered_span === 'full' ? row.declared_track_count : row.rendered_span;
          row.pass = row.computed_track_count === row.declared_track_count
            && row.implicit_track_count === 0
            && row.rendered_span_tracks === row.expected_span_tracks
            && row.overflow <= 1
            && row.field_width <= row.grid_width + 1
            && row.width_delta <= WIDTH_TOLERANCE;
          matrix.push(row);
        }
      }
    }
    const canonicalMatrix = [];
    const canonicalRuns = [];
    for (const containerWidth of CANONICAL_CONTAINER_WIDTHS) {
      for (const spans of CANONICAL_SPAN_SETS) canonicalRuns.push({ containerWidth, spans, readonlyFact: false });
    }
    // A compact readonly fact grid keeps the declared two-track face on the
    // folded widths, so the one-track fold must not stack it either.
    canonicalRuns.push({ containerWidth: 420, spans: [12, 12], readonlyFact: true });
    canonicalRuns.push({ containerWidth: 700, spans: [24, 12], readonlyFact: true });
    for (const run of canonicalRuns) {
      const measured = await measureCanonical(page, run.spans, run.containerWidth, run.readonlyFact);
      const rows = measured.children.map((child) => {
        const face = canonicalGridFace(measured.content_width, child.declared_span, run.readonlyFact);
        const isFull = face.span === 'full';
        const expectedStart = isFull ? '1' : `span ${face.span}`;
        const expectedEnd = isFull ? '-1' : 'auto';
        const widthOf = (renderedTracks) => renderedTracks * measured.track + (renderedTracks - 1) * measured.column_gap;
        const expectedWidth = Number((isFull ? measured.content_width : widthOf(face.span)).toFixed(2));
        const expectedGap = face.gap === null ? measured.column_gap : face.gap;
        return {
          declared_spans: run.spans,
          readonly_fact: run.readonlyFact,
          target_container_width: run.containerWidth,
          container_width: measured.container_width,
          content_width: measured.content_width,
          computed_track_count: measured.computed_track_count,
          expected_track_count: face.tracks,
          declared_span: child.declared_span,
          expected_placement: face.span,
          rendered_span: child.rendered_span,
          grid_column_start: child.grid_column_start,
          grid_column_end: child.grid_column_end,
          width: child.width,
          expected_width: expectedWidth,
          column_gap: measured.column_gap,
          expected_column_gap: expectedGap,
          overflow_right: child.overflow_right,
          pass: measured.computed_track_count === face.tracks
            && Math.abs(measured.column_gap - expectedGap) <= 0.01
            && child.grid_column_start === expectedStart
            && child.grid_column_end === expectedEnd
            && child.rendered_span === (isFull ? 'full' : face.span)
            && Math.abs(child.width - expectedWidth) <= 1.5
            && child.overflow_right <= 1,
        };
      });
      canonicalMatrix.push(...rows);
    }

    const screenshots = [];
    for (const entry of [
      { key: 'columns-1-span24-desktop', columns: 1, span: 24, container: 1200, viewport: { width: 1440, height: 900 } },
      { key: 'columns-2-span12-desktop', columns: 2, span: 12, container: 1200, viewport: { width: 1440, height: 900 } },
      { key: 'columns-3-span8-desktop', columns: 3, span: 8, container: 1600, viewport: { width: 1920, height: 1080 } },
      { key: 'columns-2-span16-medium', columns: 2, span: 16, container: 700, viewport: { width: 900, height: 900 } },
      { key: 'columns-1-span24-mobile', columns: 1, span: 24, container: 342, viewport: { width: 390, height: 844 } },
    ]) screenshots.push(await captureFixture(page, style, entry));
    const report = {
      schema_version: 'frontend_form_grid_span_matrix.v1',
      phase: PHASE,
      git_sha: process.env.GIT_SHA || '',
      form_section_blob: process.env.FORM_SECTION_BLOB || '',
      canonical_node_renderer_blob: process.env.CANONICAL_NODE_RENDERER_BLOB || '',
      matrix,
      canonical_matrix: canonicalMatrix,
      screenshots,
      failures: [
        ...matrix.filter((row) => !row.pass).map((row) => ({ surface: 'field_grid', ...row })),
        ...canonicalMatrix.filter((row) => !row.pass).map((row) => ({ surface: 'canonical_node_grid', ...row })),
      ],
    };
    fs.writeFileSync(REPORT, `${JSON.stringify(report, null, 2)}\n`);
    if (PHASE === 'final') check(report.failures.length === 0, `layout failures=${report.failures.length}`);
    console.log(
      `[frontend_form_grid_span_browser] ${PHASE === 'final' ? 'PASS' : 'CAPTURED'}`
      + ` field_rows=${matrix.length} canonical_rows=${canonicalMatrix.length} failures=${report.failures.length}`,
    );
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`[frontend_form_grid_span_browser] FAIL ${error.stack || error.message}`);
  process.exitCode = 2;
});
