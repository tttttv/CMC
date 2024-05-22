import { WidgetEnv } from "$/shared/types/api/enitites";
import { create } from "zustand";

interface WidgeEnvWithoutColors extends Omit<WidgetEnv, "color_palette"> {}

export interface WidgetEnvStore {
  widgetEnv: Omit<WidgeEnvWithoutColors, "color_palette">;
  setWidgetEnv: (widgetEnv: WidgeEnvWithoutColors) => void;
}

export const useWidgetEnv = create<WidgetEnvStore>((set) => ({
  widgetEnv: {
    token: null,
    chain: null,
    address: null,
    full_name: null,
    email: null,
    payment_method: null,
  },
  setWidgetEnv: (widgetEnv) => set({ widgetEnv }),
}));
