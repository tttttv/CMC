import { useStagesStore } from "$/widgets/Stages";
import { useEffect, useState } from "react";
import styles from "./index.module.scss";

const UPDATE_TIMER_TIME = 1000;
export const Timer = () => {
  const timeFromStorage = useStagesStore((state) => state.time);
  const [time, setTime] = useState<number>(0);
  useEffect(() => {
    setTime(timeFromStorage);

    const interval = setInterval(() => {
      setTime((prev) => {
        if (prev === 0) return 0;
        return prev - 1;
      });
    }, UPDATE_TIMER_TIME);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeFromStorage]);

  const formattedTime = `${`${Math.floor(time / 60)}`}:${`${time % 60}`.padStart(2, "0")}`;
  return <span className={styles.timer}>{formattedTime}</span>;
};
