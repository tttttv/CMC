import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { orderAPI } from "$/shared/api/order";
import Button from "$/shared/ui/kit/Button/Button";
import ButtonCancel from "$/shared/ui/kit/ButtonCancel/CancelButton";
import ModalWindow from "$/shared/ui/modals/ModalWindow";
import { useStagesStore } from "$/widgets/Stages";
import icon from "./icon.svg";
import styles from "./index.module.scss";

const ChangedCourse = () => {
  const queryClient = useQueryClient();
  const currency = useStagesStore((state) => state.currency);
  const { data, isLoading } = useQuery({
    queryKey: ["order"],
    queryFn: orderAPI.getOrderState,
    select: (data) => data.data,
    retry: 0,
    refetchOnWindowFocus: false,
  });
  const isWithdrawAmount = data?.state_data.hasOwnProperty("withdraw_amount");
  const newAmount = isWithdrawAmount
    ? data?.state_data.withdraw_amount
    : data?.state_data.payment_amount;
  const { mutate: cancelOrder } = useMutation({
    mutationKey: ["cancelOrder"],
    mutationFn: orderAPI.cancelOrder,
  });

  const { mutateAsync: continueOrder, isPending } = useMutation({
    mutationKey: ["continueOrder"],
    mutationFn: orderAPI.continueOrder,
  });

  return (
    <ModalWindow
      icon={<img src={icon} alt="Курс изменен" />}
      windowClassName={styles.window}
    >
      <h2 className={styles.modalTitle}>Курс выбранных валют изменился</h2>
      <p className={styles.newAmount}>
        {isWithdrawAmount
          ? "По новой цене вы получите"
          : "По новой цене вам необходимо оплатить"}{" "}
        <span className={styles.amount}>
          {isLoading ? "..." : newAmount} {currency}
        </span>
      </p>
      <Button
        disabled={isPending}
        onClick={async () => {
          await continueOrder();
          await queryClient.invalidateQueries({ queryKey: ["order"] });
        }}
      >
        {isPending ? "Подождите..." : "Продолжить с новым курсом"}
      </Button>
      <ButtonCancel onClick={cancelOrder} disabled={isPending}>
        Отмена
      </ButtonCancel>
    </ModalWindow>
  );
};

export default ChangedCourse;
