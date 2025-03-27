// src/types/navigator.d.ts

// Augment the existing Navigator interface to include getBattery
interface Navigator {
  getBattery?(): Promise<BatteryManager>;
}

// Define the BatteryManager interface based on the specification
interface BatteryManager extends EventTarget {
  readonly charging: boolean;
  readonly chargingTime: number;
  readonly dischargingTime: number;
  readonly level: number;
  onchargingchange: ((this: BatteryManager, ev: Event) => any) | null;
  onchargingtimechange: ((this: BatteryManager, ev: Event) => any) | null;
  ondischargingtimechange: ((this: BatteryManager, ev: Event) => any) | null;
  onlevelchange: ((this: BatteryManager, ev: Event) => any) | null;
}