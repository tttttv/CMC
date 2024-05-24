import { useQuery } from "@tanstack/react-query";

import styles from "../CurrencyColumnList.module.scss";

import CurrencyItem from "$/entities/CurrencyItem";
import { currencyAPI } from "$/shared/api/currency";
import clsx from "$/shared/helpers/clsx";
import useCurrencyStore from "$/shared/storage/currency";
import LoadingScreen from "$/shared/ui/global/LoadingScreen";
import ScrollableList from "$/shared/ui/other/ScrollList";
import { useWidgetEnv } from "$/pages/WidgetEnv/model/widgetEnv";
import { useEffect } from "react";

interface Props {
  changingProperty: "sending" | "getting";
}
export const CryptoList = ({ changingProperty }: Props) => {
  const {
    data: fromMethods,
    isLoading: isFromLoading,
    refetch,
  } = useQuery({
    queryKey: ["fromValues"],
    queryFn: currencyAPI.getFromValues,
    select: (data) => data.data.methods,
  });
  const { data: toMethods, isLoading: isToLoading } = useQuery({
    queryKey: ["toValues"],
    queryFn: currencyAPI.getToValues,
    select: (data) => data.data.methods,
  });

  useEffect(() => {
    refetch();
  }, [changingProperty]);

  const currency =
    changingProperty === "sending" ? fromMethods?.crypto : toMethods?.crypto;
  const isLoading =
    changingProperty === "sending" ? isFromLoading : isToLoading;

  const { token } = useWidgetEnv((state) => state.widgetEnv);
  const toCurrency = useCurrencyStore((state) => state.toCurrency);
  const setToCurrency = useCurrencyStore((state) => state.setToCurrency);
  useEffect(() => {
    if (!token) return;
    setToCurrency(token);
  }, [token]);
  return (
    <ScrollableList>
      {isLoading ? (
        <LoadingScreen inContainer>Грузим криптовалюты</LoadingScreen>
      ) : (
        <div className={styles.list}>
          {currency?.map((token) => {
            const className = clsx(
              styles.listItem,
              { [styles.active]: `${toCurrency}` === `${token.id}` },
              []
            );
            return (
              <div key={token.id} className={className}>
                <button
                  className={styles.itemButton}
                  onClick={() => setToCurrency(String(token.id))}
                ></button>
                <CurrencyItem name={token.name} image={token.logo} />
              </div>
            );
          })}
        </div>
      )}
    </ScrollableList>
  );
};
