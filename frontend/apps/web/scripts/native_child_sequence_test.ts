import assert from 'node:assert/strict';
import {
  declaredLayoutChildSegments,
  nativeChildSegments,
} from '../src/components/template/nativeChildSequence';

type TestNode = { type?: string; name?: string; text?: string };

function typeOf(node: unknown): string {
  return String((node as TestNode).type || '').trim().toLowerCase();
}

function shapes(segments: Array<{ kind: string; nodes: unknown[] }>) {
  return segments.map((segment) => [
    segment.kind,
    segment.nodes.map((node) => {
      const item = node as TestNode;
      return item.name ?? item.text ?? item.type ?? '';
    }),
  ]);
}

const mixed = [
  { type: 'field', name: 'sc_stage_required_done' },
  { type: 'text', text: '/' },
  { type: 'field', name: 'sc_stage_required_total' },
] as unknown[];

assert.deepEqual(shapes(nativeChildSegments(mixed, typeOf)), [
  ['field', ['sc_stage_required_done']],
  ['text', ['/']],
  ['field', ['sc_stage_required_total']],
]);

assert.deepEqual(shapes(declaredLayoutChildSegments(mixed, typeOf)), [
  ['field', ['sc_stage_required_done']],
  ['text', ['/']],
  ['field', ['sc_stage_required_total']],
]);
