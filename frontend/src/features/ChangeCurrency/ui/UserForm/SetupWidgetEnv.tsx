import { useWidgetEnv } from "$/pages/WidgetEnv/model/widgetEnv";
import { z } from "zod";
import { FormSchema } from "./UserForm";
import { UseFormSetValue } from "react-hook-form";
import { useEffect } from "react";

interface Props {
  setValue: UseFormSetValue<z.infer<typeof FormSchema>>;
  setChainDefaultValue: (value: string) => void;
}

const NAMING = {
  full_name: "fullName",
  address: "walletAddress",
  email: "email",
};

export const SetupWidgetEnv = ({ setValue, setChainDefaultValue }: Props) => {
  const widgetEnv = useWidgetEnv((state) => state.widgetEnv);

  useEffect(() => {
    for (const [key, value] of Object.entries(widgetEnv)) {
      if (!value) continue;

      switch (key) {
        case "chain":
          setChainDefaultValue(value as string);
          break;
        case "address":
        case "full_name":
        case "email":
          setValue(
            NAMING[key] as keyof z.infer<typeof FormSchema>,
            value as string
          );
      }
    }
  }, [widgetEnv]);
  return <></>;
};
