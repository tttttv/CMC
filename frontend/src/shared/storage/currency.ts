import { create } from "zustand";

interface CurrencyState {
  bankCurrencyType: string;
  setBankCurrencyType: (type: string) => void;

  fromCurrency: string;
  toCurrency: string;

  setFromCurrency: (currency: string) => void;
  setToCurrency: (currency: string) => void;
}
const useCurrencyStore = create<CurrencyState>((set) => ({
  bankCurrencyType: "all",
  setBankCurrencyType: (type: string) => set({ bankCurrencyType: type }),
  fromCurrency: "",
  toCurrency: "",
  setFromCurrency: (currency: string) => set({ fromCurrency: currency }),
  setToCurrency: (currency: string) => set({ toCurrency: currency }),
}));

export default useCurrencyStore;
