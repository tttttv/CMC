import { Dropdown } from "primereact/dropdown";
import { useEffect } from "react";

import styles from "./index.module.scss";

interface Props {
  value: string;
  onChange: (value: string) => void;
  options: { name: string; value: string }[];
  label: string;
  disabled?: boolean;
  defaultValue?: string;
}
const Select = (props: Props) => {
  const { value, onChange, options, disabled, label, defaultValue } = props;
  useEffect(() => {
    onChange(defaultValue || "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [defaultValue]);
  return (
    <div className={styles.selectContainer} data-disabled={disabled}>
      {label && (
        <label className={styles.label} htmlFor={label}>
          {label}
        </label>
      )}
      <Dropdown
        disabled={disabled}
        panelClassName={styles.selectPanel}
        className={styles.select}
        dropdownIcon={
          <svg
            width="10"
            height="5"
            viewBox="0 0 10 5"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M4.47422 4.475L0.849219 0.85C0.799219 0.8 0.761886 0.746 0.737219 0.688C0.712552 0.63 0.699885 0.567333 0.699219 0.5C0.699219 0.366667 0.745219 0.25 0.837219 0.15C0.929219 0.0499996 1.04989 0 1.19922 0H8.79922C8.94922 0 9.07022 0.0499996 9.16222 0.15C9.25422 0.25 9.29988 0.366667 9.29922 0.5C9.29922 0.533333 9.24922 0.65 9.14922 0.85L5.52422 4.475C5.44089 4.55833 5.35755 4.61667 5.27422 4.65C5.19089 4.68333 5.09922 4.7 4.99922 4.7C4.89922 4.7 4.80755 4.68333 4.72422 4.65C4.64089 4.61667 4.55755 4.55833 4.47422 4.475Z"
              fill="#292929"
            />
          </svg>
        }
        value={value}
        options={options}
        onChange={(e) => {
          onChange(e.value);
        }}
        emptyFilterMessage={"Ничего не найдено"}
        appendTo={"self"}
        optionLabel="name"
      />
    </div>
  );
};

export default Select;
