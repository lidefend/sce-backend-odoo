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
      matrix,
      screenshots,
      failures: matrix.filter((row) => !row.pass),
    };
    fs.writeFileSync(REPORT, `${JSON.stringify(report, null, 2)}\n`);
    if (PHASE === 'final') check(report.failures.length === 0, `layout failures=${report.failures.length}`);
    console.log(`[frontend_form_grid_span_browser] ${PHASE === 'final' ? 'PASS' : 'CAPTURED'} rows=${matrix.length} failures=${report.failures.length}`);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(`[frontend_form_grid_span_browser] FAIL ${error.stack || error.message}`);
  process.exitCode = 2;
});
