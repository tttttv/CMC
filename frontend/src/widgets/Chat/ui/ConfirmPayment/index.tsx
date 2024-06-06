import styles from "./index.module.scss";
import Button from "$/shared/ui/kit/Button/Button";
import { Timer } from "./Timer";
import OperationCancel from "$/widgets/ModalWindows/OperationCancel";
import { useState } from "react";
import Modal from "$/shared/ui/modals/Modal";
import { orderAPI } from "$/shared/api/order";
import { useMutation } from "@tanstack/react-query";

export const ConfirmPayment = () => {
  const [isModalVisible, setModalVisible] = useState(false);
  const { mutate: confirmWithdraw, isPending } = useMutation({
    mutationFn: orderAPI.confirmWithdraw,
    mutationKey: ["confirmWithdraw"],
  });
  const { mutate: openDispute, isPending: disputePending } = useMutation({
    mutationFn: orderAPI.openDispute,
    mutationKey: ["openDispute"],
  });

  return (
    <>
      <div className={styles.container}>
        <div className={styles.content}>
          <h2 className={styles.title}>Вам перечислены деньги!</h2>
          <Timer />
          <div className={styles.buttons}>
            <Button
              className={styles.confirmButton}
              onClick={() => confirmWithdraw()}
              disabled={isPending}
            >
              {isPending ? "Обрабатываем запрос" : "Подтвердить получение"}
            </Button>
            <button
              className={styles.challengeButton}
              onClick={() => setModalVisible(true)}
            >
              Оспорить
            </button>
          </div>
        </div>
      </div>
      <Modal opened={isModalVisible}>
        <OperationCancel
          closeFn={() => setModalVisible(false)}
          confirmFn={() => openDispute()}
          isPending={disputePending}
          title="Вы уверены, что хотите оспорить?"
          buttonText="Да"
        />
      </Modal>
    </>
  );
};
