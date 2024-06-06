import { useQuery } from "@tanstack/react-query";
import { Message as MessageType } from "$/shared/types/api/enitites";
import { getDateFromMessage } from "../../lib/message";

import { Message } from "$/entities/Message/ui/Message";
import { orderAPI } from "$/shared/api/order";
import LoadingScreen from "$/shared/ui/global/LoadingScreen";
import ScrollableList from "$/shared/ui/other/ScrollList";
import { useStagesStore } from "$/widgets/Stages";
import styles from "./Messages.module.scss";

const REFETCH_DELAY = 5000;

export const Messages = () => {
  const state = useStagesStore((state) => state.state);
  const { data, isLoading } = useQuery({
    queryKey: ["messages"],
    queryFn: () => {
      return orderAPI.getOrderMessages();
    },
    retry: 0,
    refetchInterval: REFETCH_DELAY,
    refetchOnWindowFocus: false,
    select: (data) => data.data,
  });

  const messages = data?.messages.sort(
    (m1, m2) => getDateFromMessage(m1) - getDateFromMessage(m2)
  );

  return (
    <ScrollableList listClassName={styles.messages}>
      {state !== "ERROR" && (
        <>
          {isLoading ? (
            <LoadingScreen inContainer>Грузим сообщения...</LoadingScreen>
          ) : (
            <>
              {messages?.map((message, index) => (
                <Message key={index} message={message as MessageType} />
              ))}
            </>
          )}
        </>
      )}
    </ScrollableList>
  );
};
