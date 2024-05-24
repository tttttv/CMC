import telegramIcon from "../images/telegram.jpg";

import styles from "./TechSupport.module.scss";

export const TechSupport = () => {
  return (
    <div className={styles.container}>
      <img src={telegramIcon} alt="Иконка телеграмма" />
      <h3 className={styles.title}>
        <a href="" target="_blank">
          www.telegram.org
        </a>
      </h3>
    </div>
  );
};
