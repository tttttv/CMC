import ChangeCurrency from "$/features/ChangeCurrency";
import { useExchangeSettings } from "$/shared/storage/exchangeSettings";
import Page from "$/shared/ui/global/Page";
import ChooseCurrency from "$/widgets/ChooseCurrency";
import styles from "./index.module.scss";

export const MainPage = () => {
  const fromType = useExchangeSettings((state) => state.fromType);
  const toType = useExchangeSettings((state) => state.toType);

  return (
    <Page>
      <div className={styles.container}>
        <ChooseCurrency
          title="Вы отправляете"
          currencyType={fromType}
          changingProperty="sending"
        />
        <ChooseCurrency
          title="Вы получаете"
          currencyType={toType}
          changingProperty="getting"
        />
        <ChangeCurrency />
      </div>
    </Page>
  );
};
