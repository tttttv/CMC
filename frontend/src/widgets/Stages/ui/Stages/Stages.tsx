import { useEffect, useRef, useState } from "react";

import { useStagesStore } from "../../model/stagesStore";

import Modal from "$/shared/ui/modals/Modal";
import FailOrder from "$/widgets/ModalWindows/FailOrder";
import SuccessOrder from "$/widgets/ModalWindows/SuccessOrder";
import styles from "./Stages.module.scss";
import { Timer } from "./Timer";

export const Stages = () => {
  const withdrawType = useStagesStore((state) => state.withdrawType);
  const state = useStagesStore((state) => state.state);
  const currency = useStagesStore((state) => state.currency);

  const stage = useRef(0);
  const statusBarRef = useRef<HTMLDivElement>(null);

  const [successStatus, setSuccessStatus] = useState(false);
  const [errorStatus, setErrorStatus] = useState(false);

  useEffect(() => {
    switch (state) {
      case "RECEIVING":
        stage.current = 1;
        break;
      case "BUYING":
        stage.current = 2;
        break;

      case "TRADING":
        stage.current = 3;
        break;

      case "WITHDRAWING":
        stage.current = 4;
        break;
      case "SUCCESS":
        setSuccessStatus(true);
        break;
      case "ERROR":
        setErrorStatus(true);
        break;

      default:
        stage.current = 0;
    }
    const statusBarHeight = parseInt(
      getComputedStyle(statusBarRef.current!).getPropertyValue(
        "--status-bar-height"
      )
    );
    const gap = parseInt(
      getComputedStyle(statusBarRef.current!).getPropertyValue("--gap")
    );
    const paddingTop = parseInt(
      getComputedStyle(statusBarRef.current!).getPropertyValue("--padding-top")
    );

    statusBarRef.current!.style.height = `${stage.current * statusBarHeight + (stage.current - 1) * gap + paddingTop}px`;

    const stagesHTML = statusBarRef.current?.parentNode?.children;
    for (let i = 0; i < (stagesHTML?.length || 0); i++) {
      stagesHTML?.[i].classList.remove(styles.active);
      if (i <= stage.current) {
        stagesHTML?.[i].classList.add(styles.active);
      }
    }
  }, [state]);

  return (
    <>
      <Timer />
      <ul className={styles.stages}>
        <Modal opened={successStatus} modalClassName={styles.modal}>
          <SuccessOrder />
        </Modal>
        <Modal opened={errorStatus} modalClassName={styles.modal}>
          <FailOrder />
        </Modal>
        <div className={styles.statusBar} ref={statusBarRef}></div>
        <li className={styles.stage}>Ожидается отправка средств</li>
        <li className={styles.stage}>Покупка {currency}</li>
        <li className={styles.stage}>Обмен {currency}</li>
        <li className={styles.stage}>Вывод {currency}</li>
      </ul>
    </>
  );
};
