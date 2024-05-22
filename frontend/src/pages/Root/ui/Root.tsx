import { Outlet } from "@tanstack/react-router";
import Wrapper from "./Wrapper";
export { useWidgetEnv } from "../../WidgetEnv/model/widgetEnv";

export const Root = () => {
  return (
    <Wrapper>
      <Outlet />
    </Wrapper>
  );
};
