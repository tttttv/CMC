import { create } from "zustand";
import { WidgetPaymentMethod, WithdrawMethod } from "../types/api/enitites";

interface ExchangeSettings {
  fromType: "crypto" | "bank";
  toType: "crypto" | "bank";
  setFromType: (type: "crypto" | "bank") => void;
  setToType: (type: "crypto" | "bank") => void;

  avaibleMethods: {
    fiat: WidgetPaymentMethod[] | null;
    crypto: WidgetPaymentMethod[] | null;
  };
  addAvaibleMethod: (method: WidgetPaymentMethod) => void;

  withdrawMethod: WithdrawMethod | null;
  setWithdrawMethod: (method: WithdrawMethod) => void;
}

export const useExchangeSettings = create<ExchangeSettings>((set) => ({
  fromType: "bank",
  toType: "crypto",

  setFromType: (type) => set({ fromType: type }),
  setToType: (type) => set({ toType: type }),

  avaibleMethods: {
    fiat: null,
    crypto: null,
  },

  addAvaibleMethod: (method) =>
    set((state) => ({
      avaibleMethods: {
        ...state.avaibleMethods,
        [method.type]: [...(state.avaibleMethods[method.type] || []), method],
      },
    })),

  withdrawMethod: {
    id: -1,
    type: "crypto",
    logo: "",
    name: "",
    chain: "",
    address: "",
  },
  setWithdrawMethod: (method) => set({ withdrawMethod: method }),
}));
