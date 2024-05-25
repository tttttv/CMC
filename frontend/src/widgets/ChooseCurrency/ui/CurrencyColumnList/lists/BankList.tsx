import { useQuery } from "@tanstack/react-query";

import styles from "../CurrencyColumnList.module.scss";

import CurrencyItem from "$/entities/CurrencyItem";
import { currencyAPI } from "$/shared/api/currency";
import clsx from "$/shared/helpers/clsx";
import useCurrencyStore from "$/shared/storage/currency";
import LoadingScreen from "$/shared/ui/global/LoadingScreen";
import ScrollableList from "$/shared/ui/other/ScrollList";
import { SettingsProps } from "../../ChooseCurrency";
import { useEffect, useState } from "react";
import { useWidgetEnv } from "$/pages/WidgetEnv/model/widgetEnv";

export const BankList = ({
  changingProperty,
}: Omit<SettingsProps, "currencyType">) => {
  const { data: fromMethods, isLoading: isFromLoading } = useQuery({
    queryKey: ["fromValues"],
    queryFn: currencyAPI.getFromValues,
    select: (data) => data.data.methods,
  });
  const {
    data: toMethods,
    isLoading: isToLoading,
    refetch,
  } = useQuery({
    queryKey: ["toValues"],
    queryFn: currencyAPI.getToValues,
    select: (data) => data.data.methods,
  });

  useEffect(() => {
    refetch();
  }, [changingProperty]);

  const bankCurrencyType = useCurrencyStore((state) => state.bankCurrencyType);

  const fromCurrency = useCurrencyStore((state) => state.fromCurrency);
  const toCurrency = useCurrencyStore((state) => state.toCurrency);

  const setFromCurrency = useCurrencyStore((state) => state.setFromCurrency);
  const setToCurrency = useCurrencyStore((state) => state.setToCurrency);
  const setCurrency =
    changingProperty === "sending" ? setFromCurrency : setToCurrency;
  const currCurrency =
    changingProperty === "sending" ? fromCurrency : toCurrency;

  const currency =
    changingProperty === "sending" ? fromMethods?.fiat : toMethods?.fiat;
  const isLoading =
    changingProperty === "sending" ? isFromLoading : isToLoading;

  const banks =
    bankCurrencyType === "all"
      ? currency?.map((bank) => bank.payment_methods).flat()
      : currency?.find((bank) => bank.id === bankCurrencyType)?.payment_methods;

  return (
    <ScrollableList>
      {isLoading ? (
        <LoadingScreen inContainer>Грузим банки</LoadingScreen>
      ) : banks?.length !== 0 ? (
        <div className={styles.list}>
          {banks?.map((bank) => {
            const className = clsx(
              styles.listItem,
              { [styles.active]: `${currCurrency}` === `${bank.id}` },
              []
            );
            return (
              <div key={bank.id} className={className}>
                <CurrencyItem name={bank.name} image={bank.logo} />
                <button
                  className={styles.itemButton}
                  onClick={() => setCurrency(String(bank.id))}
                ></button>
              </div>
            );
          })}
        </div>
      ) : (
        <span data-lack>Нет доступных банков</span>
      )}
    </ScrollableList>
  );
};
