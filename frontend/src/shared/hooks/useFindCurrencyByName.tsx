import { useEffect, useState } from "react";

import { useBanks } from "./useBanks";
import { useCurrency } from "./useCurrency";

interface Props {
  name: string;
  type: "fiat" | "crypto";
  changingProperty: "sending" | "getting";
}
export const useFindCurrencyByName = ({
  name,
  type,
  changingProperty,
}: Props) => {
  const [val, setValue] = useState<any>(null);
  const { to, from } = useCurrency();

  const currency = (changingProperty === "sending" ? from : to).data;
  const banks = useBanks(currency?.fiat, "all");

  useEffect(() => {
    const newVal =
      type === "crypto"
        ? currency?.crypto.find((crypto) => crypto.name === name)
        : banks?.find((bank) => bank.name === name);
    setValue(newVal);
  }, [currency, to, from]);

  return val;
};
