import { widgetAPI } from "$/pages/WidgetEnv/api/widget";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useWidgetEnv } from "../model/widgetEnv";
import { TinyColor } from "@ctrl/tinycolor";
import { useExchangeSettings } from "$/shared/storage/exchangeSettings";

interface Props {
  children: React.ReactNode;
  widgetId: string;
}

export const WidgetEnv = ({ children, widgetId }: Props) => {
  const setWidgetEnv = useWidgetEnv((state) => state.setWidgetEnv);
  const { addAvaibleMethod, setToType, setWithdrawMethod } =
    useExchangeSettings();

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

    const { payment_methods, withdraw_method } = widgetEnvWithoutColors;

    if (payment_methods) {
      for (const method of payment_methods) {
        addAvaibleMethod(method);
      }
    }

    if (withdraw_method) {
      setToType(withdraw_method.type === "fiat" ? "bank" : "crypto");
      setWithdrawMethod(withdraw_method);
    }

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
