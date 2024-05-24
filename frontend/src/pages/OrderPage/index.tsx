import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";

import { StateOrderPage } from "./ui/StateOrderPage";

import { orderAPI } from "$/shared/api/order";
import LoadingScreen from "$/shared/ui/global/LoadingScreen";
import { useStagesStore } from "$/widgets/Stages";
import { WaitingPage } from "./ui/WaitingPage";
import { clearOrderHash } from "$/shared/helpers/orderHash/clear";

const REFETCH_DELAY = 10000;
export const OrderPage = () => {
  const navigate = useNavigate();
  const setStage = useStagesStore((state) => state.setStage);
  const setCrypto = useStagesStore((state) => state.setCrypto);
  const setTime = useStagesStore((state) => state.setTime);
  const setNewAmount = useStagesStore((state) => state.setNewAmount);
  const { data, refetch, isLoading } = useQuery({
    queryKey: ["order"],
    queryFn: orderAPI.getOrderState,
    select: (data) => data.data,
  });

  useEffect(() => {
    const interval = setInterval(() => {
      refetch();
    }, REFETCH_DELAY);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const state = data?.state;
  useEffect(() => {
    setStage(state || "");
    setCrypto(data?.order.to.name || "");

    if (state === "PENDING" || state === "WRONG" || state === "INITIATED") {
      setTime(data?.state_data.time_left || 0);
    } else setTime(data?.order.time_left || 0);

    setNewAmount(data?.state_data?.withdraw_quantity || 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  if (
    state === "INITIALIZATION" ||
    state === "CREATED" ||
    state === "INITIATED"
  ) {
    return <LoadingScreen>Создаем заказ</LoadingScreen>;
  }

  if (state === "PENDING" || state === "WRONG") {
    return <WaitingPage state={state} isLoading={isLoading} />;
  }

  if (
    state === "RECEIVING" ||
    state === "BUYING" ||
    state === "TRADING" ||
    state === "WITHDRAWING" ||
    state === "SUCCESS" ||
    state === "ERROR"
  ) {
    return <StateOrderPage />;
  }

  if (state === "TIMEOUT") {
    clearOrderHash();
    navigate({
      to: "/$widgetId",
      params: {
        widgetId: JSON.stringify(localStorage.getItem("widgetId")),
      },
    });
  }
  return (
    <>
      Необработанный статус: <b>{state || "статус отсутствует"}</b>
    </>
  );
};
