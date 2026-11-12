export function createAttachmentViewerRequestLease() {
  let sequence = 0;
  return {
    begin(): number {
      sequence += 1;
      return sequence;
    },
    invalidate(): void {
      sequence += 1;
    },
    owns(token: number): boolean {
      return token === sequence;
    },
  };
}
