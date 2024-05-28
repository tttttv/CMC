import { useWidgetEnv } from "$/pages/WidgetEnv/model/widgetEnv";
import { z } from "zod";
import { FormSchema } from "./UserForm";
import { UseFormSetValue } from "react-hook-form";
import { useEffect } from "react";

interface Props {
  setValue: UseFormSetValue<z.infer<typeof FormSchema>>;
}

export const SetupWidgetEnv = ({ setValue }: Props) => {
  const widgetEnv = useWidgetEnv((state) => state.widgetEnv);

  useEffect(() => {
    const { email, full_name, withdraw_method } = widgetEnv;
    if (email) setValue("email", email);
    if (full_name) setValue("fullName", full_name);
    if (withdraw_method) {
      const { address } = withdraw_method;
      if (address) setValue("walletAddress", address);
    }
  }, [widgetEnv]);
  return <></>;
};
