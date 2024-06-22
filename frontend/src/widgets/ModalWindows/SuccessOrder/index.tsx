import { useNavigate } from "@tanstack/react-router";

import Button from "$/shared/ui/kit/Button/Button";
import icon from "./icon.svg";
import styles from "./index.module.scss";
import { clearOrderHash } from "$/shared/helpers/orderHash/clear";
import { useOrder } from "$/shared/hooks/useOrder";
import { Course } from "$/shared/ui/other/Course";

const SuccessOrder = () => {
  const { data } = useOrder();
  const navigate = useNavigate();
  const rate = data?.order.rate ?? 0;
  const paymentName = data?.order.payment.name ?? "unknown";
  const withdrawName = data?.order.withdraw.name ?? "unknown";
  const address =
    (data?.state_data.address?.length || 0) < 25
      ? data?.state_data.address
      : `${data?.state_data.address?.slice(0, 25)}...`;
  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <div className={styles.title}>
          <img src={icon} alt="" />
          <h2 className={styles.titleText}>Поздравляем!</h2>
        </div>
        <div className={styles.infoContainer}>
          <div className={styles.infoDescription}>
            <h3 className={styles.infoTitle}>Перевод совершен успешно</h3>
            Мы успешно перевели деньги на ваш кошелек. Если у вас возникли
            проблемы с их получением - свяжитесь с нами через телеграм @bot
          </div>
          <div className={styles.info}>
            <div className={styles.infoBlock}>
              <h4 className={styles.infoBlockTile}>Сумма</h4>
              <span className={styles.infoBlockValue}>
                {data?.order.withdraw_amount} {data?.order.withdraw?.name}
              </span>
            </div>
            <div className={styles.infoBlock}>
              <h4 className={styles.infoBlockTile}>Адрес</h4>
              <span className={styles.infoBlockValue}>{address}</span>
            </div>
            <div className={styles.infoBlock}>
              <h4 className={styles.infoBlockTile}>Курс</h4>
              <span className={styles.infoBlockValue}>
                <Course
                  rate={rate}
                  withdrawName={withdrawName}
                  paymentName={paymentName}
                />
              </span>
            </div>
          </div>
          <Button
            onClick={() => {
              navigate({
                to: "/$widgetId",
                params: {
                  widgetId: JSON.stringify(localStorage.getItem("widgetId")),
                },
              });
              clearOrderHash();
            }}
          >
            Вернуться к обменам
          </Button>
        </div>
      </div>
    </div>
  );
};

export default SuccessOrder;
