import { createFileRoute, redirect } from "@tanstack/react-router";

import { MainPage } from "$/pages/MainPage";
import getCookieValue from "$/shared/helpers/getCookie";

export const Route = createFileRoute("/$widgetId/_layout/")({
  component: MainPage,
  loader: async () => {
    const hash = getCookieValue("order_hash");
    if (hash) {
      throw redirect({
        to: "/$widgetId/order",
        params: {
          widgetId: JSON.stringify(localStorage.getItem("widgetId")),
        },
      });
    }
  },
});
