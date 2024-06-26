import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";

import OperationCancel from "../ModalWindows/OperationCancel";

import { orderAPI } from "$/shared/api/order";

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
import { queryClient } from "$/pages/Root/ui/Wrapper";
import copy from "copy-to-clipboard";

import { useCurrency } from "$/shared/hooks/useCurrency";
import { useStagesStore } from "../Stages";

const COPY_MESSAGE_DISAPPEAR_DELAY = 1500;

const MoneyWaiting = () => {
  const navigate = useNavigate();
  const [isCopied, setCopied] = useState(false);
  const [isConfirmModal, setConfirmModal] = useState(false);

  const { qData: data } = useStagesStore();

  const order = data?.order;
  const from = order?.payment;
  const to = order?.withdraw;
  const fromAmount = order?.payment_amount;
  const toAmount = order?.withdraw_amount;
  const isFirstStage = order?.stage === 1;

  const showConfirmButton = data?.state === "PENDING" && isFirstStage;

  const transferObj = isFirstStage ? from : to;
  const isTransferToCrypto = transferObj?.type === "crypto";

  const [isButtonDisabled, setButtonDisabled] = useState(false);
  const { to: toCurrency } = useCurrency();

  const chain = toCurrency.data?.crypto
    .find((cr) => cr.chains.some((chain) => chain.id === transferObj?.chain))
    ?.chains?.find((chain) => chain.id === transferObj?.chain)?.name;

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

  const refetchOrder = () => {
    queryClient.refetchQueries({
      queryKey: ["order"],
    });
  };
  const errorHandler = () => {
    refetchOrder();
    setButtonDisabled(false);
  };
  const { mutate: confirmPayment } = useMutation({
    mutationFn: orderAPI.confirmPayment,
    onSuccess: refetchOrder,
    onError: errorHandler,
  });

  const { mutate: confirmWithdraw } = useMutation({
    mutationFn: orderAPI.confirmWithdraw,
    onSuccess: refetchOrder,
    onError: errorHandler,
  });

  const confirmPay = isFirstStage ? confirmPayment : confirmWithdraw;

  const copyAddresToClipboard = () => {
    const cardNumber = data?.state_data.terms?.account_no || "";
    copy(cardNumber);
    setCopied(true);
    setTimeout(() => {
      setCopied(false);
    }, COPY_MESSAGE_DISAPPEAR_DELAY);
  };

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Ожидается получение средств</h2>

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
                imageUrl={transferObj?.logo || ""}
                width={16}
              />
            </div>
            <div className={styles.infoBlockValue}>
              {transferObj?.name || "---"}
            </div>
          </div>
        </div>
        {isTransferToCrypto && (
          <div className={styles.infoBlock}>
            <div className={styles.infoBlockTitle}>
              <ChainIcon />
              <h3 className={styles.infoBlockText}>Chain</h3>
            </div>
            <div className={styles.infoBlockValueContainer}>
              <div className={styles.infoBlockValue}>{chain || "---"}</div>
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

      {showConfirmButton && (
        <div className={styles.buttons}>
          <Button onClick={() => setConfirmModal(true)}>
            Подтвердить перевод
          </Button>
          <ButtonCancel onClick={cancelPay}>Отмена</ButtonCancel>
        </div>
      )}
      <Modal opened={isConfirmModal}>
        <OperationCancel
          isPending={isButtonDisabled}
          confirmFn={() => {
            setButtonDisabled(true);
            confirmPay();
          }}
          closeFn={() => setConfirmModal(false)}
        />
      </Modal>
    </div>
  );
};

export default MoneyWaiting;
