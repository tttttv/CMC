import { WidgetEnv } from "$/shared/types/api/enitites";
import { create } from "zustand";

interface WidgeEnvWithoutColors extends Omit<WidgetEnv, "color_palette"> {}

export interface WidgetEnvStore {
  widgetEnv: WidgeEnvWithoutColors;
  setWidgetEnv: (widgetEnv: WidgeEnvWithoutColors) => void;
}

export const useWidgetEnv = create<WidgetEnvStore>((set) => ({
  widgetEnv: {
    withdraw_method: {
      id: -1,
      type: "crypto",
      logo: "",
      name: "",
      chain: "",
      address: "",
    },
    full_name: null,
    email: null,
    payment_methods: null,
  },
  setWidgetEnv: (widgetEnv) => set({ widgetEnv }),
}));
