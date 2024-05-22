import { InputHTMLAttributes } from "react";
import { UseFormRegisterReturn } from "react-hook-form";

import { CurrencyIcon } from "../../other/CurrencyIcon";

import styles from "./index.module.scss";

const ImportantIcon = () => {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle cx="8" cy="8" r="8" fill="var(--secondaryAccentColor)" />
      <path
        d="M8.81947 10.4551C8.8168 10.456 8.57102 10.5378 8.35769 10.5378C8.23991 10.5378 8.19236 10.5133 8.17725 10.5026C8.10258 10.4506 7.96391 10.3533 8.20125 9.88043L8.64569 8.99421C8.90925 8.46798 8.94836 7.95909 8.75458 7.56087C8.59636 7.23509 8.2928 7.01154 7.90125 6.93154C7.76113 6.90286 7.61848 6.88842 7.47547 6.88843C6.65369 6.88843 6.10036 7.36843 6.07725 7.38887C6.03866 7.42288 6.01306 7.46922 6.00482 7.51999C5.99658 7.57076 6.00621 7.62281 6.03206 7.66728C6.05791 7.71174 6.09839 7.74586 6.14658 7.76382C6.19478 7.78178 6.24771 7.78247 6.29636 7.76576C6.29858 7.76487 6.5448 7.68265 6.75813 7.68265C6.87502 7.68265 6.92213 7.70709 6.9368 7.71732C7.01191 7.76976 7.15102 7.86843 6.91413 8.34043L6.46969 9.22709C6.20569 9.75376 6.16702 10.2626 6.3608 10.6604C6.51902 10.9862 6.82213 11.2098 7.21458 11.2898C7.35413 11.3178 7.49725 11.3329 7.63858 11.3329C8.4608 11.3329 9.01458 10.8529 9.03769 10.8324C9.07631 10.7985 9.10197 10.7522 9.1103 10.7015C9.11864 10.6508 9.10913 10.5987 9.08339 10.5542C9.05765 10.5097 9.01729 10.4755 8.96916 10.4575C8.92104 10.4394 8.86814 10.4385 8.81947 10.4551Z"
        fill="var(--accentColor)"
      />
      <path
        d="M8.44705 6.4439C9.0607 6.4439 9.55816 5.94644 9.55816 5.33279C9.55816 4.71914 9.0607 4.22168 8.44705 4.22168C7.8334 4.22168 7.33594 4.71914 7.33594 5.33279C7.33594 5.94644 7.8334 6.4439 8.44705 6.4439Z"
        fill="var(--accentColor)"
      />
    </svg>
  );
};
interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register?: UseFormRegisterReturn<any>;

  importantMessage?: string;
  iconUrl?: string;
  iconAlt?: string;
  disabledStyle?: boolean;
  errorText?: string;
  clearError?: () => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
}

const Input = ({
  clearError,
  onChange,
  label,
  register,
  importantMessage = "",
  iconAlt = "",
  iconUrl = "",
  errorText = "",
  disabledStyle = false,
  ...props
}: Props) => {
  return (
    <div className={styles.inputWrapper}>
      {label && (
        <label className={styles.label} htmlFor={label}>
          {label}
        </label>
      )}
      <div className={styles.inputContainer}>
        {iconUrl && iconAlt && (
          <div className={styles.icon}>
            <CurrencyIcon
              currencyName={iconAlt}
              imageUrl={iconUrl}
              width={32}
            />
          </div>
        )}
        <input
          className={styles.input}
          id={label}
          data-disabled={disabledStyle}
          {...register}
          {...props}
          onChange={(e) => {
            clearError?.();
            onChange?.(e);
          }}
        />
        {errorText && clearError && (
          <span className={styles.error}>{errorText}</span>
        )}
      </div>
      {importantMessage && (
        <label htmlFor={label} className={styles.importantMessage}>
          <ImportantIcon />
          <span>{importantMessage}</span>
        </label>
      )}
    </div>
  );
};

export default Input;
