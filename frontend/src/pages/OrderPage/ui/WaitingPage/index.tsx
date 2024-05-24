import styles from "./index.module.scss";
import LoadingScreen from "$/shared/ui/global/LoadingScreen";
import Page from "$/shared/ui/global/Page";
import Modal from "$/shared/ui/modals/Modal";
import ChangedCourse from "$/widgets/ModalWindows/СhangedCourse";
import MoneyWaiting from "$/widgets/MoneyWaiting";
import { ChatWithButton } from "../ChatWithButton/ChatWithButton";

interface Props {
  isLoading: boolean;
  state: string | undefined;
}

export const WaitingPage = ({ isLoading, state }: Props) => {
  return (
    <Page>
      <ChatWithButton maxContentWidth={519}>
        <div className={styles.container}>
          {isLoading ? (
            <LoadingScreen inContainer>Грузим заказ</LoadingScreen>
          ) : (
            <>
              <MoneyWaiting />
              <Modal opened={state === "WRONG"}>
                <ChangedCourse />
              </Modal>
            </>
          )}
        </div>
      </ChatWithButton>
    </Page>
  );
};
