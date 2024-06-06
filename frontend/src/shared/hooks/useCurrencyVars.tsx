import useCurrencyStore from "../storage/currency";
import { useExchangeSettings } from "../storage/exchangeSettings";

export const useCurrencyVars = (changingProperty: "sending" | "getting") => {
  const fromCurrency = useCurrencyStore((state) => state.fromCurrency);
  const toCurrency = useCurrencyStore((state) => state.toCurrency);

  const setFromCurrency = useCurrencyStore((state) => state.setFromCurrency);
  const setToCurrency = useCurrencyStore((state) => state.setToCurrency);

  const fromCurrencyType = useExchangeSettings((state) => state.fromType);
  const toCurrencyType = useExchangeSettings((state) => state.toType);
  return {
    currCurrency: changingProperty === "sending" ? fromCurrency : toCurrency,
    setCurrency:
      changingProperty === "sending" ? setFromCurrency : setToCurrency,
    currencyType:
      changingProperty === "sending" ? fromCurrencyType : toCurrencyType,
  };
};
