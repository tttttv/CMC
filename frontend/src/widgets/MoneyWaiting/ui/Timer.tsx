import { useEffect, useState } from "react";

import { useStagesStore } from "$/widgets/Stages";
import styles from "./Timer.module.scss";
import { clearOrderHash } from "$/shared/helpers/orderHash/clear";
import { useNavigate } from "@tanstack/react-router";

export const Timer = () => {
  const navigate = useNavigate();
  const timeFromStorage = useStagesStore((state) => state.time);
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    setSeconds(timeFromStorage);
    const interval = setInterval(() => {
      setSeconds((prev) => {
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
    }, 1000);

    return () => clearInterval(interval);
  }, [timeFromStorage]);
  const time = `${`${Math.floor(seconds / 60)}`.padStart(2, "0")}:${`${seconds % 60}`.padStart(2, "0")}`;
  return (
    <div className={styles.time}>
      Оплатите в течение <span>{time}</span> минут
    </div>
  );
};
