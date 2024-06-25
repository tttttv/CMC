import clsx from "$/shared/helpers/clsx";
import useMediaQuery from "$/shared/hooks/useMediaQuery";
import styles from "./ChatWithButton.module.scss";
import Chat from "$/widgets/Chat";
import Button from "$/shared/ui/kit/Button/Button";
import { useEffect, useRef, useState } from "react";
import { useMessages } from "$/shared/hooks/useMessages";

interface Props {
  children: React.ReactNode;
  maxContentWidth?: number;
}
export const ChatWithButton = ({ children, maxContentWidth = 0 }: Props) => {
  const { matching: isChatHide } = useMediaQuery("(max-width: 1024px)");
  const [isChatOpened, setIsChatOpened] = useState(false);
  const lastMessagesAmount = useRef<undefined | number>(undefined);
  const [newMessagesAmount, setNewMessagesAmount] = useState<number | "">("");
  const { data } = useMessages();

  const containerName = clsx(
    styles.stagesContainer,
    {
      [styles.chatOpened]: isChatOpened,
    },
    []
  );

  useEffect(() => {
    const messagesLength = data?.messages.length ?? 0;
    if (lastMessagesAmount.current === undefined) {
      lastMessagesAmount.current = messagesLength;
      return;
    }

    if (isChatOpened) return;

    if (messagesLength <= lastMessagesAmount.current) {
      setNewMessagesAmount("");
      return;
    }

    setNewMessagesAmount(messagesLength - lastMessagesAmount.current);
    lastMessagesAmount.current = messagesLength;
  }, [data]);

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
                    onClick={() => {
                      setIsChatOpened(true);
                      setNewMessagesAmount("");
                    }}
                    className={clsx(styles.chatButton, {}, [
                      newMessagesAmount === "" ? styles.hideAmount : "",
                    ])}
                    data-amount={`${newMessagesAmount}`}
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
