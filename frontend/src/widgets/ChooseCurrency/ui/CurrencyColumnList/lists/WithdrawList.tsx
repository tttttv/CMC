import { useFindCurrencyByName } from "$/shared/hooks/useFindCurrencyByName";
import useCurrencyStore from "$/shared/storage/currency";
import { useEffect } from "react";
import List from "./List";
import { useWidgetEnv } from "$/pages/WidgetEnv/model/widgetEnv";

export const WithdrawList = () => {
  const { withdrawing_token } = useWidgetEnv((state) => state.widgetEnv);

  const setTo = useCurrencyStore((state) => state.setToCurrency);
  const findedMethod = useFindCurrencyByName({
    name: withdrawing_token,
    type: "crypto",
    changingProperty: "getting",
  });

  useEffect(() => {
    setTo(`${findedMethod?.id}`);
  }, [findedMethod]);

  return <List items={[findedMethod]} changingProperty={"getting"} />;
};
