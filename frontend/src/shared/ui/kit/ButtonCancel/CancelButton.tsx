import { ReactNode } from "@tanstack/react-router";

import styles from "./CancelButton.module.scss";
import { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  onClick?: () => void;
}

export default function ButtonCancel({
  children,
  onClick,
  ...props
}: ButtonProps) {
  return (
    <>
      <button className={styles.buttonCancel} onClick={onClick} {...props}>
        {children}
      </button>
    </>
  );
}
