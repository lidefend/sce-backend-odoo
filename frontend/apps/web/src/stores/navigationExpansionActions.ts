/** Persist only presentation expansion state; navigation authority stays server-owned. */
interface NavigationExpansionStore {
  menuExpandedKeys: string[];
  scenarioExpandedCenters: string[];
  scenarioExpandedScenarios: string[];
  persist(): void;
}

export const navigationExpansionActions = {
    toggleMenuExpanded(this: NavigationExpansionStore, key: string) {
      const set = new Set(this.menuExpandedKeys);
      if (set.has(key)) {
        set.delete(key);
      } else {
        set.add(key);
      }
      this.menuExpandedKeys = [...set];
      this.persist();
    },
    ensureMenuExpanded(this: NavigationExpansionStore, keys: string[]) {
      const set = new Set(this.menuExpandedKeys);
      let changed = false;
      keys.forEach((key) => {
        if (!set.has(key)) {
          set.add(key);
          changed = true;
        }
      });
      if (changed) {
        this.menuExpandedKeys = [...set];
        this.persist();
      }
    },
    toggleScenarioCenter(this: NavigationExpansionStore, key: string) {
      const set = new Set(this.scenarioExpandedCenters);
      if (set.has(key)) {
        set.delete(key);
      } else {
        set.add(key);
      }
      this.scenarioExpandedCenters = [...set];
      this.persist();
    },
    toggleScenarioExpanded(this: NavigationExpansionStore, key: string) {
      const set = new Set(this.scenarioExpandedScenarios);
      if (set.has(key)) {
        set.delete(key);
      } else {
        set.add(key);
      }
      this.scenarioExpandedScenarios = [...set];
      this.persist();
    },
    ensureScenarioExpanded(this: NavigationExpansionStore, centerKey: string, scenarioKey: string) {
      const centerSet = new Set(this.scenarioExpandedCenters);
      const scenarioSet = new Set(this.scenarioExpandedScenarios);
      let changed = false;
      if (centerKey && !centerSet.has(centerKey)) {
        centerSet.add(centerKey);
        changed = true;
      }
      if (scenarioKey && !scenarioSet.has(scenarioKey)) {
        scenarioSet.add(scenarioKey);
        changed = true;
      }
      if (changed) {
        this.scenarioExpandedCenters = [...centerSet];
        this.scenarioExpandedScenarios = [...scenarioSet];
        this.persist();
      }
    },
};
