import Select from "$/shared/ui/kit/Select";
import { Controller } from "react-hook-form";

interface Props {
  control: any;
  chains: any[];
  isChainBlocked: boolean;
  setChain: (chain: string) => void;
  chainDefaultValue: string;
  label: string;
  name: string;
}

export const ChainSelect = ({ props }: { props: Props }) => {
  const {
    control,
    chains,
    isChainBlocked,
    setChain,
    chainDefaultValue,
    label,
    name,
  } = props;
  return (
    <Controller
      control={control}
      name={name}
      defaultValue={chainDefaultValue}
      rules={{ required: "Поле должно быть заполнено" }}
      render={({ field: { onChange, value } }) => (
        <Select
          disabled={isChainBlocked || chains.length === 0}
          defaultValue={chainDefaultValue}
          onChange={(value: string) => {
            onChange(value);
            setChain(value);
          }}
          value={value}
          options={chains.map((chain) => ({
            name: chain.name,
            value: chain.id,
          }))}
          label={label}
        />
      )}
    />
  );
};
