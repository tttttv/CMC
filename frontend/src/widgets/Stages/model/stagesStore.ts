import { create } from "zustand";

interface StagesState {
  time: number;
  state: string;
  currency: string;
  newAmount: number;
  withdrawType: "crypto" | "fiat" | undefined;
  setCurrency: (currency: string) => void;
  setState: (state: string) => void;
  setTime: (time: number) => void;
  setNewAmount: (amount: number) => void;
  setWithdrawType: (withdraw: "crypto" | "fiat" | undefined) => void;
}
export const useStagesStore = create<StagesState>((set) => {
  return {
    time: 0,
    state: "",
    currency: "",
    withdrawType: undefined,
    newAmount: 0,
    setCurrency: (currency: string) => set({ currency }),
    setState: (state: string) => set({ state }),
    setTime: (time: number) => set({ time }),
    setNewAmount: (amount: number) => set({ newAmount: amount }),
    setWithdrawType: (withdraw) => set({ withdrawType: withdraw }),
  };
});
