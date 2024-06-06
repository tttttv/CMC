import { WidgetEnv } from "$/shared/types/api/enitites";
import { create } from "zustand";

interface WidgeEnvWithoutColors extends Omit<WidgetEnv, "color_palette"> {}

export interface WidgetEnvStore {
  widgetEnv: WidgeEnvWithoutColors;
  setWidgetEnv: (widgetEnv: WidgeEnvWithoutColors) => void;
}

export const useWidgetEnv = create<WidgetEnvStore>((set) => ({
  widgetEnv: {
    partner_code: "",
    partner_commission: 0,
    withdrawing_address: "",
    withdrawing_token: "",
    withdrawing_chain: "",
    redirect_url: "",
    email: "",
    name: "",
  },
  setWidgetEnv: (widgetEnv) => set({ widgetEnv }),
}));
