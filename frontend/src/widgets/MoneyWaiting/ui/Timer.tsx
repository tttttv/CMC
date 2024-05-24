import { useEffect, useState } from "react";

import { useStagesStore } from "$/widgets/Stages";
import styles from "./Timer.module.scss";

export const Timer = () => {
  const timeFromStorage = useStagesStore((state) => state.time);
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    setSeconds(timeFromStorage);
    const interval = setInterval(() => {
      setSeconds((prev) => {
        if (prev <= 0) {
          return 0;
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
