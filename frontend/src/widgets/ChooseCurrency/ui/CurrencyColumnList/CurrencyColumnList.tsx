import { useWidgetEnv } from "$/pages/WidgetEnv/model/widgetEnv";

import { SettingsProps } from "../ChooseCurrency";
import { BankList } from "./lists/BankList";
import { CryptoList } from "./lists/CryptoList";

import { WithdrawList } from "./lists/WithdrawList";

export const CurrencyColumnList = ({
  currencyType,
  changingProperty,
}: SettingsProps) => {
  const { withdrawing_token } = useWidgetEnv((state) => state.widgetEnv);

  if (withdrawing_token && changingProperty === "getting")
    return <WithdrawList />;

  // const avaibleMethods = useExchangeSettings((state) => state.avaibleMethods);
  // if (currencyType === "crypto" && avaibleMethods.crypto)
  //   return (
  //     <List items={avaibleMethods.crypto} changingProperty={changingProperty} />
  //   );

  // if (currencyType === "bank" && avaibleMethods.fiat) {
  //   return (
  //     <List items={avaibleMethods.fiat} changingProperty={changingProperty} />
  //   );
  // }

  return currencyType === "crypto" ? (
    <CryptoList changingProperty={changingProperty} />
  ) : (
    <BankList changingProperty={changingProperty} />
  );
};
