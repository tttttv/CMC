import { Control, Controller } from "react-hook-form";
import Input from "../Input";
import { validateCardInput } from "./lib/validation";

interface Props {
  name: string;
  control: Control<any, any>;
  error: string | undefined;
  label: string;
  setValue: (value: string) => void;
  setError: (error: string) => void;
  clearErrors: () => void;
}

export const BankCardInput = (props: Props) => {
  const { control, name, clearErrors, setValue, setError, error, label } =
    props;
  return (
    <Controller
      control={control}
      name={name}
      render={({ field: { onChange, ...field } }) => (
        <Input
          label={label}
          {...field}
          onChange={(e) => {
            const newValue = validateCardInput(e.target.value);
            if (
              newValue.errorStatus === "ONE_LETTER" ||
              newValue.errorStatus === "LETTER"
            ) {
              if (newValue.errorStatus === "ONE_LETTER") {
                setValue("");
              }
              setError("Можно вводить только цифры!");
              return;
            }
            if (newValue.errorStatus === "LENGTH") return;

            onChange(newValue.value);
          }}
          errorText={error}
          clearError={clearErrors}
        />
      )}
    />
  );
};
