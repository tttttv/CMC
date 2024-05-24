import { SettingsProps } from "../ChooseCurrency";
import { BankList } from "./lists/BankList";

export const CurrencyRowList = ({
  currencyType,
  changingProperty,
}: SettingsProps) =>
  currencyType === "crypto" ? (
    <></>
  ) : (
    <BankList changingProperty={changingProperty} />
  );
