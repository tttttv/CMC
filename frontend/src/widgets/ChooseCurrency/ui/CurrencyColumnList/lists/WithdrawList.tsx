import { useFindCurrencyByName } from "$/shared/hooks/useFindCurrencyByName";
import useCurrencyStore from "$/shared/storage/currency";
import { useExchangeSettings } from "$/shared/storage/exchangeSettings";
import { useEffect } from "react";
import List from "./List";

export const WithdrawList = () => {
  const withdrawMethod = useExchangeSettings((state) => state.withdrawMethod);

  const setTo = useCurrencyStore((state) => state.setToCurrency);
  const findedMethod = useFindCurrencyByName({
    name: withdrawMethod?.name || "",
    type: withdrawMethod?.type || "crypto",
    changingProperty: "getting",
  });

  useEffect(() => {
    setTo(`${findedMethod?.id}`);
  }, [findedMethod]);

  if (!findedMethod) return <>Не смогли найти нужную валюту!</>;
  return <List items={[findedMethod]} changingProperty={"getting"} />;
};
