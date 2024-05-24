import clsx from "$/shared/helpers/clsx";
import useMediaQuery from "$/shared/hooks/useMediaQuery";
import { useState } from "react";
import styles from "./ChatWithButton.module.scss";
import Chat from "$/widgets/Chat";
import Button from "$/shared/ui/kit/Button/Button";
interface Props {
  children: React.ReactNode;
  maxContentWidth?: number;
}
export const ChatWithButton = ({ children, maxContentWidth = 0 }: Props) => {
  const { matching: isChatHide } = useMediaQuery("(max-width: 1024px)");
  const [isChatOpened, setIsChatOpened] = useState(false);
  const containerName = clsx(
    styles.stagesContainer,
    {
      [styles.chatOpened]: isChatOpened,
    },
    []
  );
  return (
    <div className={containerName}>
      {!isChatOpened ? (
        <>
          <div className={styles.left}>
            {children}
            {isChatHide && (
              <>
                <div
                  className={styles.chatButtonContainer}
                  style={
                    maxContentWidth
                      ? { maxWidth: `${maxContentWidth}px`, width: "100%" }
                      : undefined
                  }
                >
                  <Button
                    onClick={() => setIsChatOpened(true)}
                    className={styles.chatButton}
                    data-amount="1"
                  >
                    Открыть чат
                  </Button>
                </div>
              </>
            )}
          </div>
          {!isChatHide && <Chat />}
        </>
      ) : (
        <div className={styles.chatContainer}>
          <Chat />
          <div className={styles.chatButtonContainer}>
            <Button onClick={() => setIsChatOpened(false)}>
              Вернуться к обмену
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
