import { useQuery } from "@tanstack/react-query";

import styles from "../CurrencyColumnList.module.scss";

import CurrencyItem from "$/entities/CurrencyItem";
import { currencyAPI } from "$/shared/api/currency";
import clsx from "$/shared/helpers/clsx";
import useCurrencyStore from "$/shared/storage/currency";
import LoadingScreen from "$/shared/ui/global/LoadingScreen";
import ScrollableList from "$/shared/ui/other/ScrollList";
import { useWidgetEnv } from "$/pages/WidgetEnv/model/widgetEnv";
import { useEffect, useState } from "react";
import { useBlockedUiStore } from "$/shared/storage/blockedUi";

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

  const currency = changingProperty === "sending" ? [] : toMethods?.crypto;
  const isLoading =
    changingProperty === "sending" ? isFromLoading : isToLoading;

  const { token } = useWidgetEnv((state) => state.widgetEnv);

  const fromCurrency = useCurrencyStore((state) => state.fromCurrency);
  const toCurrency = useCurrencyStore((state) => state.toCurrency);

  const setFromCurrency = useCurrencyStore((state) => state.setFromCurrency);
  const setToCurrency = useCurrencyStore((state) => state.setToCurrency);
  const setCurrency =
    changingProperty === "sending" ? setFromCurrency : setToCurrency;
  const currCurrency =
    changingProperty === "sending" ? fromCurrency : toCurrency;
  const { setTokenAlreadyBlocked, isTokenAlreadyBlocked } = useBlockedUiStore();
  const isBlocked = isTokenAlreadyBlocked === changingProperty && !!token;
  useEffect(() => {
    if (!token || isTokenAlreadyBlocked) return;
    setCurrency(token);
    setTokenAlreadyBlocked(changingProperty);
  }, [token]);

  return (
    <ScrollableList listClassName={styles.listContainer}>
      {isLoading ? (
        <LoadingScreen inContainer>Грузим криптовалюты</LoadingScreen>
      ) : currency?.length !== 0 ? (
        <div className={styles.list}>
          {currency?.map((token) => {
            const className = clsx(
              styles.listItem,
              { [styles.active]: `${currCurrency}` === `${token.id}` },
              []
            );
            return (
              <div key={token.id} className={className}>
                <button
                  disabled={isBlocked}
                  className={styles.itemButton}
                  onClick={() => setCurrency(String(token.id))}
                ></button>
                <CurrencyItem name={token.name} image={token.logo} />
              </div>
            );
          })}
        </div>
      ) : (
        <span data-lack>Нет доступных криптовалют</span>
      )}
    </ScrollableList>
  );
};
