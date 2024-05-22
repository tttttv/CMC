import { widgetAPI } from "$/pages/WidgetEnv/api/widget";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useWidgetEnv } from "../model/widgetEnv";
import { TinyColor } from "@ctrl/tinycolor";

interface Props {
  children: React.ReactNode;
  widgetId: string;
}

export const WidgetEnv = ({ children, widgetId }: Props) => {
  const setWidgetEnv = useWidgetEnv((state) => state.setWidgetEnv);
  const { data, isSuccess, refetch } = useQuery({
    queryKey: ["widgetEnv"],
    queryFn: () => widgetAPI.getWidgetEnv(widgetId),
    select: (data) => data.data,
  });

  useEffect(() => {
    refetch();
  }, [widgetId]);

  useEffect(() => {
    if (!isSuccess) return;

    const { color_palette: colorScheme, ...widgetEnvWithoutColors } = data;

    setWidgetEnv(widgetEnvWithoutColors);
    // const colorScheme = {
    //   bodyColor: "green",
    //   blockColor: "pink",
    //   textColor: "#DE87",
    //   secondaryTextColor: "beige",
    //   accentColor: "red",
    //   secondaryAccentColor: "orange",
    // };
    if (!colorScheme) return;

    const bodyCSS = getComputedStyle(document.body);
    for (const [colorName, color] of Object.entries(colorScheme)) {
      const isVarExist = bodyCSS.getPropertyValue(`--${colorName}`);

      if (!isVarExist || !color || !new TinyColor(color).isValid) return;

      document.body.style.setProperty(`--${colorName}`, `${color}`);
    }
  }, [isSuccess]);
  return <>{children}</>;
};
