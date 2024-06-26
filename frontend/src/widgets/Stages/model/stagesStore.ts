import { OrderState } from "$/shared/types/api/enitites";
import { create } from "zustand";

interface StagesState {
  time: number;
  stage: 1 | 2 | -1 | number;
  state: string;
  currency: string;
  newAmount: number;
  withdrawType: "crypto" | "fiat" | undefined;
  qData: OrderState | null;
  setQData: (qData: OrderState | null) => void;
  setCurrency: (currency: string) => void;
  setState: (state: string) => void;
  setTime: (time: number) => void;
  setNewAmount: (amount: number) => void;
  setWithdrawType: (withdraw: "crypto" | "fiat" | undefined) => void;
  setStage: (stage: 1 | 2 | -1) => void;
}
export const useStagesStore = create<StagesState>((set) => ({
  time: 0,
  state: "",
  stage: -1,
  currency: "",
  withdrawType: undefined,
  newAmount: 0,
  qData: null,
  setCurrency: (currency: string) => set({ currency }),
  setState: (state: string) => set({ state }),
  setTime: (time: number) => set({ time }),
  setNewAmount: (amount: number) => set({ newAmount: amount }),
  setWithdrawType: (withdraw) => set({ withdrawType: withdraw }),
  setStage: (stage) => set({ stage }),
  setQData: (qData) => set({ qData }),
}));
