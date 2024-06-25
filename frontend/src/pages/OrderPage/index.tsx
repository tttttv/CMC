import { useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";

import { StateOrderPage } from "./ui/StateOrderPage";

import LoadingScreen from "$/shared/ui/global/LoadingScreen";
import { useStagesStore } from "$/widgets/Stages";
import { WaitingPage } from "./ui/WaitingPage";
import { clearOrderHash } from "$/shared/helpers/orderHash/clear";

import { useQuery } from "@tanstack/react-query";
import { orderAPI } from "$/shared/api/order";

export const OrderPage = () => {
  const navigate = useNavigate();
  const {
    setState,
    setTime,
    setCurrency,
    setNewAmount,
    setWithdrawType,
    setQData,
    setStage,
  } = useStagesStore();

  const { data, isLoading } = useQuery({
    queryKey: ["order"],
    queryFn: orderAPI.getOrderState,
    select: (data) => data.data,
    retry: false,
    refetchInterval: 10000,
  });
  const state = data?.state;
  useEffect(() => {
    setState(state || "");
    setCurrency(data?.order.withdraw.name ?? "");
    setNewAmount(data?.state_data.withdraw_amount ?? 0);
    setStage((data?.order.stage ?? -1) as -1 | 1 | 2);
    setWithdrawType(data?.order.withdraw.type);
    setQData(data ?? null);

    if (state === "PENDING" || state === "INITIATED") {
      setTime(data?.state_data.time_left || 0);
    } else setTime(data?.order.time_left || 0);

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
  return <LoadingScreen></LoadingScreen>;
  // return (
  //   <>
  //     Необработанный статус: <b>{state || "статус отсутствует"}</b>
  //     <button
  //       onClick={() => {
  //         clearOrderHash();
  //         navigate({
  //           to: "/$widgetId",
  //           params: {
  //             widgetId: JSON.stringify(localStorage.getItem("widgetId")),
  //           },
  //         });
  //       }}
  //     >
  //       вернуться
  //     </button>
  //   </>
  // );
};
