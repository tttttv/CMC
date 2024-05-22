import { createFileRoute, redirect } from "@tanstack/react-router";

import { OrderPage } from "$/pages/OrderPage";
import getCookieValue from "$/shared/helpers/getCookie";

export const Route = createFileRoute("/$widgetId/_layout/order/")({
  component: OrderPage,
  loader: async () => {
    const hash = getCookieValue("order_hash");
    if (!hash) {
      throw redirect({
        to: "/$widgetId",
        params: {
          widgetId: JSON.stringify(localStorage.getItem("widgetId")),
        },
      });
    }
  },
});
