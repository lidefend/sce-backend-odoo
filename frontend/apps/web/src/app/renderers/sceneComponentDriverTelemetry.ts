export type SceneComponentDriverTelemetryEvent = {
  timestamp: number;
  actionId: number;
  model: string;
  requestedKit: string;
  resolvedKit: string;
  source: string;
  reasonCode: string;
};

const MAX_EVENTS = 60;
const events: SceneComponentDriverTelemetryEvent[] = [];

export function recordSceneComponentDriverEvent(event: SceneComponentDriverTelemetryEvent): void {
  events.push(Object.freeze({ ...event }));
  if (events.length > MAX_EVENTS) events.splice(0, events.length - MAX_EVENTS);
}

export function readSceneComponentDriverTelemetry(): readonly SceneComponentDriverTelemetryEvent[] {
  return events.map((event) => ({ ...event }));
}
