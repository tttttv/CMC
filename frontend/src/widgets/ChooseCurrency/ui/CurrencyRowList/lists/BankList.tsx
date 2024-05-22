import { useQuery } from "@tanstack/react-query";

import styles from "../CurrencyRowList.module.scss";

import { currencyAPI } from "$/shared/api/currency";
import clsx from "$/shared/helpers/clsx";
import useCurrencyStore from "$/shared/storage/currency";

interface Props {
  changingProperty: "sending" | "getting";
}

export const BankList = ({ changingProperty }: Props) => {
  const { data: fromMethods } = useQuery({
    queryKey: ["fromValues"],
    queryFn: currencyAPI.getFromValues,
    select: (data) => data.data.methods,
  });

  const { data: toMethods } = useQuery({
    queryKey: ["toValues"],
    queryFn: currencyAPI.getToValues,
    select: (data) => data.data.methods,
  });

  const setCurrencyType = useCurrencyStore(
    (state) => state.setBankCurrencyType
  );

  const currencyItems =
    changingProperty === "sending" ? fromMethods?.fiat : toMethods?.fiat;

  const currencyType = useCurrencyStore((state) => state.bankCurrencyType);

  return (
    <>
      {currencyItems?.length !== 0 && (
        <ul className={styles.list}>
          <li
            className={clsx(
              styles.listItem,
              { [styles.active]: currencyType === "all" },
              []
            )}
          >
            <button onClick={() => setCurrencyType("all")}>Все</button>
          </li>
          {currencyItems?.map((currency) => {
            const className = clsx(
              styles.listItem,
              {
                [styles.active]: currency.id === currencyType,
              },
              []
            );

            const setCurrency = () => {
              setCurrencyType(currency.id);
            };

            return (
              <li key={currency.id} className={className}>
                <button onClick={setCurrency}>{currency.name}</button>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
};
