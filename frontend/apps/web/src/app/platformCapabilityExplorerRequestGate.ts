export type CapabilityExplorerRequestGate = {
  begin: () => number;
  isCurrent: (requestSequence: number) => boolean;
  invalidate: () => void;
};

export function createCapabilityExplorerRequestGate(): CapabilityExplorerRequestGate {
  let latestSequence = 0;
  return {
    begin() {
      latestSequence += 1;
      return latestSequence;
    },
    isCurrent(requestSequence: number) {
      return requestSequence === latestSequence;
    },
    invalidate() {
      latestSequence += 1;
    },
  };
}
