import { TitledBlock } from "$/shared/ui/global/TitledBlock";

import { ChooseButtons } from "./ChooseButtons/ChooseButtons";

import { CurrencyColumnList } from "./CurrencyColumnList/CurrencyColumnList";
import { CurrencyRowList } from "./CurrencyRowList/CurrencyRowList";

export interface SettingsProps {
  currencyType: "bank" | "crypto";
  changingProperty: "getting" | "sending";
}

interface Props extends SettingsProps {
  title: string;
}

export const ChooseCurrency = ({
  title,
  currencyType,
  changingProperty,
}: Props) => {
  return (
    <TitledBlock title={title}>
      <ChooseButtons
        changingProperty={changingProperty}
        currencyType={currencyType}
      />
      <CurrencyRowList
        currencyType={currencyType}
        changingProperty={changingProperty}
      />
      <CurrencyColumnList
        currencyType={currencyType}
        changingProperty={changingProperty}
      />
    </TitledBlock>
  );
};
