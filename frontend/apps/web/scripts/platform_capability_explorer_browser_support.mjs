export function createExpectedHttpFailureBudget() {
  const expectations = [];

  return {
    arm({ status, intent, count = 1 }) {
      if (!Number.isInteger(status) || status < 400 || status > 599) {
        throw new Error('expected HTTP failure status must be a 4xx or 5xx integer');
      }
      if (!Number.isInteger(count) || count < 1) {
        throw new Error('expected HTTP failure count must be a positive integer');
      }
      expectations.push({
        status,
        intent: String(intent || ''),
        remaining: count,
      });
    },
    consume({ status, intent }) {
      const requestIntent = String(intent || '');
      const expectation = expectations.find((item) => (
        item.remaining > 0
        && item.status === status
        && (!item.intent || item.intent === requestIntent)
      ));
      if (!expectation) return false;
      expectation.remaining -= 1;
      return true;
    },
    pending() {
      return expectations.reduce((total, item) => total + item.remaining, 0);
    },
  };
}
