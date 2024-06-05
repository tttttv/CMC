import { useExchangeSettings } from "$/shared/storage/exchangeSettings";
import { SettingsProps } from "../ChooseCurrency";
import { BankList } from "./lists/BankList";
import { CryptoList } from "./lists/CryptoList";
import List from "./lists/List";
import { WithdrawList } from "./lists/WithdrawList";

export const CurrencyColumnList = ({
  currencyType,
  changingProperty,
}: SettingsProps) => {
  const withdrawMethod = useExchangeSettings((state) => state.withdrawMethod);

  if (withdrawMethod?.name && changingProperty === "getting")
    return <WithdrawList />;

  const avaibleMethods = useExchangeSettings((state) => state.avaibleMethods);
  if (currencyType === "crypto" && avaibleMethods.crypto)
    return (
      <List items={avaibleMethods.crypto} changingProperty={changingProperty} />
    );

  if (currencyType === "bank" && avaibleMethods.fiat) {
    return (
      <List items={avaibleMethods.fiat} changingProperty={changingProperty} />
    );
  }

  return currencyType === "crypto" ? (
    <CryptoList changingProperty={changingProperty} />
  ) : (
    <BankList changingProperty={changingProperty} />
  );
};
