export type RendererSemver = readonly [number, number, number];
export type RendererContractVersionRange = {
  readonly minimum: RendererSemver;
  readonly maximumExclusive: RendererSemver;
};

const SEMVER = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/;
const RANGE = /^>=((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)) <((?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*))$/;

function tuple(value: string): RendererSemver | null {
  const match = SEMVER.exec(value);
  return match
    ? Object.freeze([Number(match[1]), Number(match[2]), Number(match[3])] as const)
    : null;
}

function compare(left: RendererSemver, right: RendererSemver): number {
  for (let index = 0; index < 3; index += 1) {
    if (left[index] !== right[index]) return left[index] - right[index];
  }
  return 0;
}

export function parseRendererVersion(value: string): RendererSemver | null {
  return tuple(String(value || '').trim());
}

export function parseRendererContractVersionRange(value: string): RendererContractVersionRange | null {
  const match = RANGE.exec(String(value || '').trim());
  if (!match) return null;
  const minimum = tuple(match[1]);
  const maximumExclusive = tuple(match[2]);
  if (!minimum || !maximumExclusive || compare(minimum, maximumExclusive) >= 0) return null;
  return Object.freeze({ minimum, maximumExclusive });
}

export function rendererSupportsContractVersion(range: string, contractVersion: string): boolean {
  const parsedRange = parseRendererContractVersionRange(range);
  const parsedVersion = parseRendererVersion(contractVersion);
  if (!parsedRange || !parsedVersion) return false;
  return compare(parsedVersion, parsedRange.minimum) >= 0
    && compare(parsedVersion, parsedRange.maximumExclusive) < 0;
}
