import useCurrencyStore from "$/shared/storage/currency";
import { useExchangeSettings } from "$/shared/storage/exchangeSettings";
import usePlaceOrder from "$/shared/storage/placeOrder";
import { PaymentMethod, Crypto } from "$/shared/types/api/enitites";
import { Course } from "$/shared/ui/other/Course";
import styles from "./CurrencyInputs.module.scss";

interface Props {
  getPricing: string | null;
  fromCurrency: PaymentMethod | Crypto | undefined;
  toCurrency: PaymentMethod | Crypto | undefined;
  betterAmount: string;
}

export const ExchangeRate = ({
  getPricing,
  fromCurrency,
  toCurrency,
  betterAmount,
}: Props) => {
  const { fromType, toType } = useExchangeSettings();
  const { price } = usePlaceOrder();
  const bankType = useCurrencyStore((state) => state.bankCurrencyType);
  const paymentName =
    fromType === "bank"
      ? bankType === "all"
        ? "RUB"
        : bankType
      : fromCurrency?.name ?? "unknown";
  const withdrawName =
    toType === "bank"
      ? bankType === "all"
        ? "RUB"
        : bankType
      : toCurrency?.name ?? "unknown";
  return (
    <div className={styles.exchangeRate}>
      <h3 className={styles.exchangeRateTitle}>
        <span className={styles.exchangeRateText}>Курс обмена</span>
        <span className={styles.exchangeRateValue}>
          {price && fromCurrency && toCurrency ? (
            <>
              {getPricing === null && (
                <Course
                  rate={+price ?? 0}
                  paymentName={paymentName ?? "unknown"}
                  withdrawName={withdrawName ?? "unknown"}
                />
              )}
            </>
          ) : (
            "---"
          )}
        </span>
      </h3>
      <h3 className={styles.exchangeRateTitle}>
        <span className={styles.exchangeRateText}>Курс выгоднее с</span>
        <span className={styles.exchangeRateValue}>
          {fromCurrency && betterAmount && toCurrency ? (
            <>
              {getPricing !== null ? "..." : betterAmount}{" "}
              {/* {fromType === "bank"
                ? bankType === "all"
                  ? "RUB"
                  : bankType
                : fromCurrency?.name} */}
              RUB
            </>
          ) : (
            "---"
          )}
        </span>
      </h3>
    </div>
  );
};
