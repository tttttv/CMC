import { create } from "zustand";

interface ExchangeSettings {
  fromType: "crypto" | "bank";
  toType: "crypto" | "bank";

  setFromType: (type: "crypto" | "bank") => void;
  setToType: (type: "crypto" | "bank") => void;
}

export const useExchangeSettings = create<ExchangeSettings>((set) => ({
  fromType: "bank",
  toType: "crypto",

  setFromType: (type) => set({ fromType: type }),
  setToType: (type) => set({ toType: type }),
}));
