import { useEffect, useState } from "react";

import { useStagesStore } from "../../model/stagesStore";

import styles from "./Timer.module.scss";
import { clearOrderHash } from "$/shared/helpers/orderHash/clear";
import { useNavigate } from "@tanstack/react-router";

const UPDATE_TIMER_TIME = 1000;
export const Timer = () => {
  const timeFromStorage = useStagesStore((state) => state.time);
  const navigate = useNavigate();
  const [time, setTime] = useState<number>(0);
  useEffect(() => {
    setTime(timeFromStorage);

    const interval = setInterval(() => {
      setTime((prev) => {
        if (prev <= 0) {
          clearOrderHash();
          navigate({
            to: "/$widgetId",
            params: {
              widgetId: JSON.stringify(localStorage.getItem("widgetId")),
            },
          });
        }
        return prev - 1;
      });
    }, UPDATE_TIMER_TIME);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeFromStorage]);

  const formattedTime = `${`${Math.floor(time / 60)}`.padStart(2, "0")}:${`${time % 60}`.padStart(2, "0")}`;

  return (
    <span className={styles.waitTime}>
      Ожидайте проведения платежа. Максимальное время ожидания:{" "}
      <div className={styles.time}>{formattedTime}</div>
    </span>
  );
};
