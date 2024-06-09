import useMediaQuery from "$/shared/hooks/useMediaQuery";
import Page from "$/shared/ui/global/Page";
import { TitledBlock } from "$/shared/ui/global/TitledBlock";
import { ConfirmPayment } from "$/widgets/Chat";
import ExchangeDetails from "$/widgets/ExchangeDetails";
import OrderStages, { useStagesStore } from "$/widgets/Stages";
import { useEffect, useRef } from "react";
import { ChatWithButton } from "../ChatWithButton/ChatWithButton";

export const StateOrderPage = () => {
  const { matching: isConfirmPaymentNotInChat } = useMediaQuery(
    "(max-width: 1024px)"
  );

  const state = useStagesStore((state) => state.state);
  const stage = useStagesStore((state) => state.stage);
  const withdrawType = useStagesStore((state) => state.withdrawType);
  const showConfirmPayment =
    withdrawType === "fiat" && state === "WITHDRAWING" && stage === 2;
  const anchorRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (isConfirmPaymentNotInChat && anchorRef.current) {
      anchorRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [isConfirmPaymentNotInChat]);

  return (
    <Page>
      <ChatWithButton>
        <ExchangeDetails />
        <OrderStages />
        {isConfirmPaymentNotInChat && showConfirmPayment && (
          <TitledBlock title="">
            <ConfirmPayment />
            <span ref={anchorRef} className="visually-hidden"></span>
          </TitledBlock>
        )}
      </ChatWithButton>
    </Page>
  );
};
