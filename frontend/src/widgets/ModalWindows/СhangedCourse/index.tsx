import { useMutation, useQueryClient } from "@tanstack/react-query";

import { orderAPI } from "$/shared/api/order";
import Button from "$/shared/ui/kit/Button/Button";
import ButtonCancel from "$/shared/ui/kit/ButtonCancel/CancelButton";
import ModalWindow from "$/shared/ui/modals/ModalWindow";
import { useStagesStore } from "$/widgets/Stages";
import icon from "./icon.svg";
import styles from "./index.module.scss";

const ChangedCourse = () => {
  const queryClient = useQueryClient();
  const newAmount = useStagesStore((state) => state.newAmount);
  const crypto = useStagesStore((state) => state.crypto);
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
        По новой цене вы получите{" "}
        <span className={styles.amount}>
          {newAmount} {crypto}
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
