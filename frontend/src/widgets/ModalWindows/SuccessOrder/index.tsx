import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";

import { orderAPI } from "$/shared/api/order";
import Button from "$/shared/ui/kit/Button/Button";
import icon from "./icon.svg";
import styles from "./index.module.scss";
import { clearOrderHash } from "$/shared/helpers/orderHash/clear";

const SuccessOrder = () => {
  const { data } = useQuery({
    queryKey: ["order"],
    queryFn: orderAPI.getOrderState,
    select: (data) => data.data,
  });
  const navigate = useNavigate();
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
                {data?.order.rate.toFixed(2)} {data?.order.payment.name} = 1{" "}
                {data?.order.withdraw?.name}
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
