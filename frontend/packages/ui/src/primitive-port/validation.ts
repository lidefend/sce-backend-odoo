import {
  PRIMITIVE_REQUIRED_CAPABILITIES,
  PRIMITIVE_SUPPORTED_CAPABILITIES,
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

const KNOWN_CAPABILITIES = new Set<string>(
  Object.values(PRIMITIVE_SUPPORTED_CAPABILITIES).flat(),
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
    if (!Array.isArray(capabilities)) {
      return fail(primitive, 'capabilities', 'capabilities must be a string array');
    }
    const declaredCapabilities: string[] = [];
    for (const capability of capabilities) {
      if (typeof capability !== 'string') {
        return fail(primitive, 'capabilities', 'capabilities must be a string array');
      }
      declaredCapabilities.push(capability);
    }
    const declared = new Set(declaredCapabilities);
    if (declared.size !== declaredCapabilities.length) {
      return fail(primitive, 'capabilities', 'capabilities must not contain duplicates');
    }
    const allowed = new Set<string>(PRIMITIVE_SUPPORTED_CAPABILITIES[primitive]);
    for (const capability of declaredCapabilities) {
      if (!KNOWN_CAPABILITIES.has(capability)) {
        return fail(primitive, capability, `unknown capability ${capability}`);
      }
      if (!allowed.has(capability)) {
        return fail(
          primitive,
          capability,
          `capability ${capability} is not supported by ${primitive}`,
        );
      }
    }
    for (const required of PRIMITIVE_REQUIRED_CAPABILITIES[primitive]) {
      if (!declared.has(required)) {
        return fail(primitive, required, 'required capability is missing');
      }
    }
  }

  return { ok: true };
}
