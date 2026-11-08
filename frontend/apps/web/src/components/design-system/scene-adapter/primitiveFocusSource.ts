import type { PrimitiveEventSource } from '@sc/ui/primitive-port';

export function createPrimitiveFocusSourceTracker() {
  let source: PrimitiveEventSource = 'programmatic';

  function onDocumentKeydown(event: KeyboardEvent) {
    if (event.isTrusted) source = 'keyboard';
  }

  return {
    bind() {
      document.addEventListener('keydown', onDocumentKeydown, true);
    },
    unbind() {
      document.removeEventListener('keydown', onDocumentKeydown, true);
    },
    pointer() {
      source = 'pointer';
    },
    keyboard() {
      source = 'keyboard';
    },
    programmatic() {
      source = 'programmatic';
    },
    consume(): PrimitiveEventSource {
      const resolved = source;
      source = 'programmatic';
      return resolved;
    },
  };
}
