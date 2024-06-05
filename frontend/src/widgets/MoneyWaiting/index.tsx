import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import OperationCancel from "../ModalWindows/OperationCancel";

import { orderAPI } from "$/shared/api/order";
import getCookieValue from "$/shared/helpers/getCookie";
import Button from "$/shared/ui/kit/Button/Button";
import ButtonCancel from "$/shared/ui/kit/ButtonCancel/CancelButton";
import Modal from "$/shared/ui/modals/Modal";
import { CurrencyIcon } from "$/shared/ui/other/CurrencyIcon";

import styles from "./index.module.scss";
import { Timer } from "./ui/Timer";
import { CopyIcon } from "./icons/CopyIcon";
import { UserIcon } from "./icons/UserIcon";
import { CardIcon } from "./icons/CardIcon";
import { BankIcon } from "./icons/BankIcon";
import { Arrow } from "./icons/Arrow";
import { clearOrderHash } from "$/shared/helpers/orderHash/clear";

const COPY_MESSAGE_DISAPPEAR_DELAY = 1500;

const MoneyWaiting = () => {
  const navigate = useNavigate();
  const [isCopied, setCopied] = useState(false);
  const [isConfirmModal, setConfirmModal] = useState(false);

  const hash = getCookieValue("order_hash");

  const { data } = useQuery({
    queryKey: ["order", hash],
    queryFn: orderAPI.getOrderState,
    retry: 0,
    select: (data) => data.data,
  });

  const order = data?.order;
  const from = order?.from;
  const to = order?.to;

  const { mutate: cancelPay } = useMutation({
    mutationKey: ["cancelPay"],
    mutationFn: orderAPI.cancelOrder,
    onSuccess: () => {
      clearOrderHash();
      navigate({
        to: "/$widgetId",
        params: {
          widgetId: JSON.stringify(localStorage.getItem("widgetId")),
        },
      });
    },
  });

  const { mutate: payOrder, isPending } = useMutation({
    mutationFn: orderAPI.payOrder,
  });

  const copyCardNumberToClipboard = () => {
    const cardNumber = data?.state_data.terms?.account_no || "";
    navigator.clipboard.writeText(cardNumber).then(() => {
      setCopied(true);
      setTimeout(() => {
        setCopied(false);
      }, COPY_MESSAGE_DISAPPEAR_DELAY);
    });
  };

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Ожидается отправка средств</h2>

      <div className={styles.changeMoney}>
        <h3 className={styles.titleSubsection}>Вы меняете:</h3>
        <div className={styles.cards}>
          <div className={styles.firstPlace}>
            <div className={styles.icon}>
              <CurrencyIcon
                currencyName={from?.name || ""}
                imageUrl={from?.logo || ""}
                width={16}
              />
            </div>
            <h4 className={styles.currency}>
              {data?.order.amount || "---"} {data?.order.from.name || ""}
            </h4>
          </div>
          <Arrow />
          <div className={styles.secondPlace}>
            <div className={styles.icon}>
              <CurrencyIcon
                currencyName={to?.name || ""}
                imageUrl={to?.logo || ""}
                width={16}
              />
            </div>
            <h2 className={styles.currency}>
              {data?.order.quantity || "---"} {to?.name || ""}
            </h2>
          </div>
        </div>
      </div>

      <div className={styles.orderInfo}>
        <div className={styles.infoBlock}>
          <div className={styles.infoBlockTitle}>
            <BankIcon />
            <h3 className={styles.infoBlockText}>Банк</h3>
          </div>
          <div className={styles.infoBlockValueContainer} data-special="bank">
            <div className={styles.icon}>
              <CurrencyIcon
                currencyName={""}
                imageUrl={from?.logo || ""}
                width={16}
              />
            </div>
            <div className={styles.infoBlockValue}>{from?.name || "---"}</div>
          </div>
        </div>
        <div className={styles.infoBlock}>
          <div className={styles.infoBlockTitle}>
            <CardIcon />
            <h3 className={styles.infoBlockText}>Номер карты</h3>
          </div>
          <div className={styles.infoBlockValueContainer}>
            <div className={styles.infoBlockValue}>
              {data?.state_data.terms?.account_no || "0000 0000 0000 0000"}
            </div>
            <button
              className={styles.copyButton}
              onClick={copyCardNumberToClipboard}
            >
              <CopyIcon />
              {isCopied && (
                <div className={styles.copyMessage}>Скопировано</div>
              )}
            </button>
          </div>
        </div>
        <div className={styles.infoBlock}>
          <div className={styles.infoBlockTitle}>
            <UserIcon />
            <h3 className={styles.infoBlockText}>ФИО</h3>
          </div>
          <div className={styles.infoBlockValueContainer}>
            <div className={styles.infoBlockValue}>
              {data?.state_data.terms?.real_name || "Неизвестное имя"}
            </div>
          </div>
        </div>
      </div>
      <div className={styles.description}>{data?.state_data.commentary}</div>
      <Timer />

      <div className={styles.buttons}>
        <Button onClick={() => setConfirmModal(true)}>
          Подтвердить перевод
        </Button>
        <ButtonCancel onClick={cancelPay}>Отмена</ButtonCancel>
      </div>
      <Modal opened={isConfirmModal}>
        <OperationCancel
          isPending={isPending}
          confirmFn={payOrder}
          closeFn={() => setConfirmModal(false)}
        />
      </Modal>
    </div>
  );
};

export default MoneyWaiting;
