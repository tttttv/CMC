import useCurrencyStore from "../storage/currency";

export const useCurrencyVars = (changingProperty: "sending" | "getting") => {
  const fromCurrency = useCurrencyStore((state) => state.fromCurrency);
  const toCurrency = useCurrencyStore((state) => state.toCurrency);

  const setFromCurrency = useCurrencyStore((state) => state.setFromCurrency);
  const setToCurrency = useCurrencyStore((state) => state.setToCurrency);

  return {
    currCurrency: changingProperty === "sending" ? fromCurrency : toCurrency,
    setCurrency:
      changingProperty === "sending" ? setFromCurrency : setToCurrency,
  };
};
