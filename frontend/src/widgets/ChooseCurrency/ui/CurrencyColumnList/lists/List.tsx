import CurrencyItem from "$/entities/CurrencyItem";
import clsx from "$/shared/helpers/clsx";
import { useCurrencyVars } from "$/shared/hooks/useCurrencyVars";

import LoadingScreen from "$/shared/ui/global/LoadingScreen";
import ScrollableList from "$/shared/ui/other/ScrollList";
import { memo } from "react";
import styles from "../CurrencyColumnList.module.scss";

interface Props {
  changingProperty: "sending" | "getting";
  isLoading?: boolean;
  items?: any[];
}
const List = ({ changingProperty, items, isLoading }: Props) => {
  const { setCurrency, currCurrency } = useCurrencyVars(changingProperty);

  return (
    <ScrollableList listClassName={styles.listContainer}>
      {isLoading ? (
        <LoadingScreen inContainer>Грузим криптовалюты</LoadingScreen>
      ) : items?.length !== 0 ? (
        <div className={styles.list}>
          {items?.map((item) => {
            const className = clsx(
              styles.listItem,
              { [styles.active]: `${currCurrency}` === `${item?.id}` },
              []
            );
            return (
              <div key={item?.id} className={className}>
                <button
                  className={styles.itemButton}
                  onClick={() => {
                    setCurrency(String(item?.id));
                  }}
                ></button>
                <CurrencyItem name={item?.name} image={item?.logo} />
              </div>
            );
          })}
        </div>
      ) : (
        <span data-lack>Нет доступных криптовалют</span>
      )}
    </ScrollableList>
  );
};

export default memo(List);
