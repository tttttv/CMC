import WidgetEnv from "$/pages/WidgetEnv";
import { Outlet, createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/$widgetId/_layout")({
  component: WidgetEnvLayout,
  beforeLoad: async (data) => {
    const { widgetId } = data.params;
    localStorage.setItem("widgetId", JSON.stringify(widgetId));
  },
});

function WidgetEnvLayout() {
  const { widgetId } = Route.useParams();

  return (
    <WidgetEnv widgetId={widgetId}>
      <Outlet />
    </WidgetEnv>
  );
}
