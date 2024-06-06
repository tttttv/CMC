import { useWidgetEnv } from "$/pages/WidgetEnv/model/widgetEnv";
import { z } from "zod";
import { UseFormSetValue } from "react-hook-form";
import { useEffect } from "react";
import { FormSchema } from "../../lib/formSchema";

interface Props {
  setValue: UseFormSetValue<z.infer<typeof FormSchema>>;
}

export const SetupWidgetEnv = ({ setValue }: Props) => {
  const widgetEnv = useWidgetEnv((state) => state.widgetEnv);

  useEffect(() => {
    const { email, name, withdrawing_address } = widgetEnv;
    if (email) setValue("email", email);
    if (name) setValue("fullName", name);
    if (withdrawing_address) {
      setValue("toWalletAddress", withdrawing_address);
    }
  }, [widgetEnv]);
  return <></>;
};
