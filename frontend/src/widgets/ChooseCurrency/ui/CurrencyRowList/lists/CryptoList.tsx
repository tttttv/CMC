import styles from "../CurrencyRowList.module.scss";

import clsx from "$/shared/helpers/clsx";

export const CryptoList = () => {
  const currencyItems = [{ id: "crypto", name: "Криптовалюты" }];

  return (
    <ul className={styles.list}>
      {currencyItems.map((currency) => {
        const className = clsx(
          styles.listItem,
          {
            [styles.active]: currency.id === "crypto",
          },
          []
        );
        return (
          <li key={currency.id} className={className}>
            {currency.name}
          </li>
        );
      })}
    </ul>
  );
};
