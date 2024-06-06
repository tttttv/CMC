import { useCurrency } from "$/shared/hooks/useCurrency";
import arrows from "../images/arrows.jpg";
import useCurrencyStore from "$/shared/storage/currency";
import { useExchangeSettings } from "$/shared/storage/exchangeSettings";
import Input from "$/shared/ui/kit/Input";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import styles from "./CurrencyInputs.module.scss";
import { useQuery } from "@tanstack/react-query";
import { currencyAPI } from "$/shared/api/currency";
import usePlaceOrder from "$/shared/storage/placeOrder";
import { validateCurrencyInput } from "../../lib/validation";

import { ErrorModal } from "$/shared/ui/modals/ErrorModal";
import { AxiosError } from "axios";
import { PriceAnchor } from "$/shared/types/api/params";
import { ExchangeRate } from "./RateInfo";

const DELAY = 1000;
export const ChangeInputs = () => {
  const { to, from } = useCurrency();
  const { setPrice, fromChain, toChain, setOrderData } = usePlaceOrder();
  const { fromType, toType } = useExchangeSettings();
  const bankType = useCurrencyStore((state) => state.bankCurrencyType);
  const fromCurrencyId = useCurrencyStore((state) => state.fromCurrency);
  const toCurrencyId = useCurrencyStore((state) => state.toCurrency);

  // GET FROM AND TO CURRENCIES
  const fromCurrency = useMemo(() => {
    if (fromType === "bank") {
      if (bankType.toLowerCase() === "all") {
        return from.data?.fiat
          .map((f) => f.payment_methods)
          .flat()
          .find((p) => `${p.id}` === `${fromCurrencyId}`);
      } else {
        return from.data?.fiat
          .find((f) => `${f.id}` === bankType)
          ?.payment_methods.find((p) => `${p.id}` === `${fromCurrencyId}`);
      }
    } else {
      return from.data?.crypto.find((c) => `${c.id}` === `${fromCurrencyId}`);
    }
  }, [fromType, bankType, fromCurrencyId, from.data]);

  const toCurrency = useMemo(() => {
    if (toType === "bank") {
      if (bankType.toLowerCase() === "all") {
        return to.data?.fiat
          .map((f) => f.payment_methods)
          .flat()
          .find((p) => `${p.id}` === `${toCurrencyId}`);
      } else {
        return to.data?.fiat
          .find((f) => `${f.id}` === bankType)
          ?.payment_methods.find((p) => `${p.id}` === `${toCurrencyId}`);
      }
    } else {
      return to.data?.crypto.find((c) => `${c.id}` === `${toCurrencyId}`);
    }
  }, [fromType, bankType, toCurrencyId, to.data]);

  const isInputsDisabled = !toCurrency || !fromCurrency;

  const [fromValue, setFromValue] = useState("");
  const [toValue, setToValue] = useState("");
  const [betterAmount, setBetterAmount] = useState("");

  // Обнуляем инпуты при смене крипты на банк и т.д.
  const resetInputValue = useCallback((e: Event) => {
    const type = (e as CustomEvent).detail;
    if (type === "to") {
      setFromValue("");
    } else setToValue("");
  }, []);

  useEffect(() => {
    const fn = (e: Event) => resetInputValue(e);
    window.addEventListener("resetInputValue", fn);
    return () => window.removeEventListener("resetInputValue", fn);
  }, []);

  const [getPricing, setGetPricing] = useState<"from" | "to" | null>(null);
  const isFromGetting = getPricing === "from";
  const isToGetting = getPricing === "to";
  const isFromInputDisabled = isInputsDisabled || isFromGetting;
  const isToInputDisabled = isInputsDisabled || isToGetting;

  const errorCode = useRef<number>(-1);
  const [hasError, setHasError] = useState(false);

  const {
    refetch: getPrice,
    error,
    data,
  } = useQuery({
    queryKey: ["getPrice"],
    queryFn: () => {
      const amount = isFromGetting ? +toValue : +fromValue;
      const anchor = (isFromGetting ? "BUY" : "SELL") as PriceAnchor;

      return currencyAPI.getPrice({
        anchor,
        amount,
        payment_method: +(fromCurrency?.id ?? -1),
        payment_amount: +fromValue,
        payment_chain: fromChain,
        withdraw_method: +(toCurrency?.id ?? -1),
        withdraw_chain: toChain,
        withdraw_amount: +toValue,
      });
    },
    enabled: false,
  });

  // Получили новые данные
  useEffect(() => {
    if (!data) return;

    const amountName = isFromGetting ? "payment_amount" : "withdraw_amount";
    const newAmount = `${data?.data[amountName] || "0"}`;

    if (isFromGetting) {
      setFromValue(newAmount);
    } else setToValue(newAmount);

    const { item_buy, item_sell, price_buy, price_sell, price, better_amount } =
      data.data;

    setOrderData({
      item_buy,
      item_sell,
      price_buy,
      price_sell,
      payment_amount: +fromValue,
      withdraw_amount: +toValue,
      anchor: isFromGetting ? "BUY" : "SELL",
    });

    setPrice(price);
    setBetterAmount((better_amount ?? "").toString());
    setGetPricing(null);
  }, [data]);

  useEffect(() => {
    if (!error || (error as any)?.response?.status === 500) return;
    const { code: newErrorCode } = (error as AxiosError<{ code: number }>)
      ?.response?.data || {
      code: -1,
    };

    const amount = isFromGetting ? toValue : fromValue;
    if (newErrorCode == 3 && amount === "0") {
      if (isFromGetting) setFromValue("0");
      else setToValue("0");
      setGetPricing(null);
      setOrderData(null);
      return;
    }
    errorCode.current = +(error || -1);
    setFromValue("0");
    setToValue("0");
    setHasError(true);
    setPrice("");
    setBetterAmount("");
    setGetPricing(null);
    setOrderData(null);
  }, [error]);

  // to/from currency update
  useEffect(() => {
    if (!fromCurrency || !fromValue || !toCurrencyId) return;
    setGetPricing("to");
    gettingTimer.current = setTimeout(() => {
      getPrice();
    }, DELAY);
  }, [toCurrency]);
  useEffect(() => {
    if (!toCurrency || !toValue || !fromCurrencyId) return;
    setGetPricing("from");
    gettingTimer.current = setTimeout(() => {
      getPrice();
    }, DELAY);
  }, [fromCurrency]);

  const gettingTimer = useRef<NodeJS.Timeout>();

  return (
    <>
      {hasError && (
        <ErrorModal
          text={
            errorCode.current === 3
              ? "Ошибка получения цены. Попробуйте другую цену или другой способ пополнения"
              : ""
          }
          closeFunction={() => {
            errorCode.current = -1;
            setHasError(false);
          }}
          useMyFunction
        />
      )}
      <div className={styles.changeInputs}>
        <Input
          disabled={isFromInputDisabled}
          value={isFromGetting ? "Рассчитываем..." : fromValue}
          onChange={(e) => {
            clearTimeout(gettingTimer.current);

            const validatedValue = validateCurrencyInput(e.target.value);
            if (!validatedValue) return;

            setFromValue(validatedValue);
            setGetPricing("to");
            gettingTimer.current = setTimeout(() => {
              getPrice();
            }, DELAY);
          }}
          disabledStyle={true}
          label="Отдаете"
          iconUrl={fromCurrency?.logo}
          iconAlt={fromCurrencyId}
        />
        <Input
          disabled={isToInputDisabled}
          value={isToGetting ? "Рассчитываем..." : toValue}
          onChange={(e) => {
            clearTimeout(gettingTimer.current);

            const validatedValue = validateCurrencyInput(e.target.value);
            if (!validatedValue) return;

            setToValue(validatedValue);
            setGetPricing("from");

            gettingTimer.current = setTimeout(() => {
              getPrice();
            }, DELAY);
          }}
          disabledStyle={true}
          label="Получаете"
          iconUrl={toCurrency?.logo}
          iconAlt={toCurrencyId}
        />

        <ExchangeRate
          fromCurrency={fromCurrency}
          toCurrency={toCurrency}
          getPricing={getPricing}
          betterAmount={betterAmount}
        />

        {!isInputsDisabled && fromValue && getPricing === null && (
          <button
            className={styles.refetchButton}
            onClick={() => {
              setGetPricing("to");
              getPrice();
            }}
          >
            <img src={arrows} alt="запрос курса" />
          </button>
        )}
      </div>
    </>
  );
};
