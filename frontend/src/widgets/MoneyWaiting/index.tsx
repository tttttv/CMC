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
import { CryptoIcon } from "./icons/CryptoIcon";
import { CryptoWalletIcon } from "./icons/CryptoWalletIcon";
import { ChainIcon } from "./icons/ChainIcon";

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
  const from = order?.payment;
  const to = order?.withdraw;
  const fromAmount = order?.payment_amount;
  const toAmount = order?.withdraw_amount;
  const stage = order?.stage;

  const isTransferToCrypto = from?.type === "crypto";
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

  const { mutate: confirmPayment, isPending: paymentPending } = useMutation({
    mutationFn: orderAPI.confirmPayment,
  });

  const { mutate: confirmWithdraw, isPending: withdrawPending } = useMutation({
    mutationFn: orderAPI.confirmWithdraw,
  });

  const confirmPay = stage === 1 ? confirmPayment : confirmWithdraw;
  const pending = stage === 1 ? paymentPending : withdrawPending;

  const copyAddresToClipboard = () => {
    const cardNumber = data?.state_data.terms?.address || "";
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
              {fromAmount || "---"} {from?.name || ""}
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
              {toAmount || "---"} {to?.name || ""}
            </h2>
          </div>
        </div>
      </div>

      <div className={styles.orderInfo}>
        <div className={styles.infoBlock}>
          <div className={styles.infoBlockTitle}>
            {isTransferToCrypto ? <CryptoIcon /> : <BankIcon />}
            <h3 className={styles.infoBlockText}>
              {isTransferToCrypto ? "Криптовалюта" : "Банк"}
            </h3>
          </div>
          <div className={styles.infoBlockValueContainer} data-special="icon">
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
        {isTransferToCrypto && (
          <div className={styles.infoBlock}>
            <div className={styles.infoBlockTitle}>
              <ChainIcon />
              <h3 className={styles.infoBlockText}>Chain</h3>
            </div>
            <div className={styles.infoBlockValueContainer}>
              <div className={styles.infoBlockValue}>
                {data?.state_data.terms.chain || "---"}
              </div>
            </div>
          </div>
        )}
        <div className={styles.infoBlock}>
          <div className={styles.infoBlockTitle}>
            {isTransferToCrypto ? <CryptoWalletIcon /> : <CardIcon />}
            <h3 className={styles.infoBlockText}>
              {isTransferToCrypto ? "Адрес кошелька" : "Номер карты"}
            </h3>
          </div>
          <div className={styles.infoBlockValueContainer}>
            <div className={styles.infoBlockValue}>
              {data?.state_data.terms?.account_no || "---"}
            </div>
            <button
              className={styles.copyButton}
              onClick={copyAddresToClipboard}
            >
              <CopyIcon />
              {isCopied && (
                <div className={styles.copyMessage}>Скопировано</div>
              )}
            </button>
          </div>
        </div>
        {!isTransferToCrypto && (
          <div className={styles.infoBlock}>
            <div className={styles.infoBlockTitle}>
              <UserIcon />
              <h3 className={styles.infoBlockText}>ФИО</h3>
            </div>
            <div className={styles.infoBlockValueContainer}>
              <div className={styles.infoBlockValue}>
                {data?.state_data.terms?.real_name ?? "Неизвестное имя"}
              </div>
            </div>
          </div>
        )}
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
          isPending={pending}
          confirmFn={confirmPay}
          closeFn={() => setConfirmModal(false)}
        />
      </Modal>
    </div>
  );
};

export default MoneyWaiting;
