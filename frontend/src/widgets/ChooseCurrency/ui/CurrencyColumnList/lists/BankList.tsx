import { useBanks } from "$/shared/hooks/useBanks";
import { useCurrency } from "$/shared/hooks/useCurrency";
import useCurrencyStore from "$/shared/storage/currency";
import List from "./List";

interface Props {
  changingProperty: "sending" | "getting";
}
export const BankList = ({ changingProperty }: Props) => {
  const { to, from } = useCurrency();
  const bankCurrencyType = useCurrencyStore((state) => state.bankCurrencyType);
  const currency =
    changingProperty === "sending" ? from?.data?.fiat : to?.data?.fiat;
  const banks = useBanks(currency, bankCurrencyType);

  return <List items={banks} changingProperty={changingProperty} />;
};
