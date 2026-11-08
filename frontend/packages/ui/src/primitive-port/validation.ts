import {
  PRIMITIVE_REQUIRED_CAPABILITIES,
  SCENE_PRIMITIVE_NAMES,
  type ScenePrimitiveName,
} from './types';

export interface ScenePrimitiveContractErrorDetail {
  code: 'SCENE_PRIMITIVE_CONTRACT_ERROR';
  primitive: ScenePrimitiveName;
  capability: string;
  detail: string;
}

export class ScenePrimitiveContractError extends Error {
  readonly detail: ScenePrimitiveContractErrorDetail;

  constructor(detail: ScenePrimitiveContractErrorDetail) {
    super(`${detail.primitive}:${detail.capability}: ${detail.detail}`);
    this.name = 'ScenePrimitiveContractError';
    this.detail = detail;
  }
}

export type PrimitiveAdapterValidationResult =
  | { ok: true }
  | { ok: false; error: ScenePrimitiveContractError };

const VALID_CAPABILITIES = new Set<string>(
  Object.values(PRIMITIVE_REQUIRED_CAPABILITIES).flat(),
);

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function fail(
  primitive: ScenePrimitiveName,
  capability: string,
  detail: string,
): PrimitiveAdapterValidationResult {
  return {
    ok: false,
    error: new ScenePrimitiveContractError({
      code: 'SCENE_PRIMITIVE_CONTRACT_ERROR',
      primitive,
      capability,
      detail,
    }),
  };
}

export function validatePrimitiveAdapterRuntimeShape(
  adapter: unknown,
): PrimitiveAdapterValidationResult {
  const firstPrimitive = SCENE_PRIMITIVE_NAMES[0];
  if (!isRecord(adapter)) {
    return fail(firstPrimitive, 'adapter', 'adapter must be an object');
  }

  for (const primitive of SCENE_PRIMITIVE_NAMES) {
    const binding = adapter[primitive];
    if (!isRecord(binding)) {
      return fail(primitive, 'binding', 'binding is missing');
    }

    const component = binding.component;
    if (!component || (typeof component !== 'function' && !isRecord(component))) {
      return fail(primitive, 'component', 'component must be a Vue component');
    }

    const contract = binding.contract;
    if (!isRecord(contract)) {
      return fail(primitive, 'contract', 'contract metadata is missing');
    }
    if (contract.primitive !== primitive) {
      return fail(
        primitive,
        'identity',
        `contract identity must be ${primitive}, received ${String(contract.primitive)}`,
      );
    }
    if (contract.portVersion !== 1) {
      return fail(primitive, 'portVersion', 'portVersion must be 1');
    }

    const capabilities = contract.capabilities;
    if (!Array.isArray(capabilities) || capabilities.some((item) => typeof item !== 'string')) {
      return fail(primitive, 'capabilities', 'capabilities must be a string array');
    }
    const declared = new Set(capabilities);
    if (declared.size !== capabilities.length) {
      return fail(primitive, 'capabilities', 'capabilities must not contain duplicates');
    }
    const invalid = capabilities.find((item) => !VALID_CAPABILITIES.has(item));
    if (invalid) {
      return fail(primitive, 'capabilities', `unsupported capability ${invalid}`);
    }
    for (const required of PRIMITIVE_REQUIRED_CAPABILITIES[primitive]) {
      if (!declared.has(required)) {
        return fail(primitive, required, 'required capability is missing');
      }
    }
  }

  return { ok: true };
}
