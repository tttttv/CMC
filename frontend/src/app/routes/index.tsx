import { createFileRoute, redirect } from "@tanstack/react-router";
import { MainPage } from "$/pages/MainPage";
import getCookieValue from "$/shared/helpers/getCookie";

export const Route = createFileRoute("/")({
  component: MainPage,
  beforeLoad: () => {
    localStorage.removeItem("widgetId");
  },
  loader: async () => {
    const hash = getCookieValue("order_hash");
    if (hash) {
      throw redirect({
        to: "/order",
      });
    }
  },
});
