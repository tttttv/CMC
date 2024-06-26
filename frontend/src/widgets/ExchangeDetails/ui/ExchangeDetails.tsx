import { useQuery } from "@tanstack/react-query";

import { orderAPI } from "$/shared/api/order";
import { TitledBlock } from "$/shared/ui/global/TitledBlock";
import { CurrencyIcon } from "$/shared/ui/other/CurrencyIcon";
import styles from "./ExchangeDetails.module.scss";
import { Arrow } from "./images/Arrow";
import { Course } from "$/shared/ui/other/Course";

export const ExchangeDetails = () => {
  const { data } = useQuery({
    queryKey: ["order"],
    queryFn: orderAPI.getOrderState,
    retry: 0,
    select: (data) => data.data,
  });

  const order = data?.order;
  const from = order?.payment;
  const to = order?.withdraw;
  const fromAmount = order?.payment_amount;
  const toAmount = order?.withdraw_amount;

  return (
    <div className={styles.container}>
      <TitledBlock title="Обмен валюты" hasBackground={false}>
        <div className={styles.currencyExchange}>
          <div className={styles.currency}>
            <h3 className={styles.currencyTitle}>Отправляете</h3>
            <div className={styles.currencyInfo}>
              <div className={styles.currencyIcon}>
                <CurrencyIcon
                  currencyName={from?.name || ""}
                  imageUrl={from?.logo || "undefined"}
                  width={32}
                />
              </div>
              <span className={styles.currencyName}>
                {fromAmount} {from?.name}
              </span>
            </div>
          </div>
          <Arrow />
          <div className={styles.currency}>
            <h3 className={styles.currencyTitle}>Получаете</h3>
            <div className={styles.currencyInfo}>
              <div className={styles.currencyIcon}>
                <CurrencyIcon
                  currencyName={to?.name || ""}
                  imageUrl={to?.logo || ""}
                  width={32}
                />
              </div>
              <span className={styles.currencyName}>
                {toAmount} {to?.name}
              </span>
            </div>
          </div>
        </div>
      </TitledBlock>
      <TitledBlock title="Детали обмена" hasBackground={false}>
        <div className={styles.exchangeRate}>
          <h3 className={styles.exchangeRateTitle}>
            <span className={styles.exchangeRateText}>Курс обмена</span>
            {data?.order.rate && from?.name && to?.name ? (
              <span className={styles.exchangeRateValue} data-color="green">
                <Course
                  rate={+data?.order.rate ?? 0}
                  paymentName={from?.name ?? "unknown"}
                  withdrawName={to?.name ?? "unknown"}
                />
              </span>
            ) : (
              <>---</>
            )}
          </h3>
          <h3 className={styles.exchangeRateTitle}>
            <span className={styles.exchangeRateText}>Номер обмена</span>
            <span className={styles.exchangeRateValue}>
              {(data?.order.order_hash || "---").toString()}
            </span>
          </h3>
        </div>
      </TitledBlock>
    </div>
  );
};
