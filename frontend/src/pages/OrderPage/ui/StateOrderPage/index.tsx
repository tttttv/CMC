import Page from "$/shared/ui/global/Page";
import ExchangeDetails from "$/widgets/ExchangeDetails";
import OrderStages from "$/widgets/Stages";
import { ChatWithButton } from "../ChatWithButton/ChatWithButton";

export const StateOrderPage = () => {
  return (
    <Page>
      <ChatWithButton>
        <ExchangeDetails />
        <OrderStages />
      </ChatWithButton>
    </Page>
  );
};
