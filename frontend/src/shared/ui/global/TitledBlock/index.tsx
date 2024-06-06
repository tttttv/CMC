import clsx from "$/shared/helpers/clsx";
import styles from "./index.module.scss";

interface Props {
  title: string;
  children: React.ReactNode;
  hasBackground?: boolean;
}

export const TitledBlock = ({
  title,
  children,
  hasBackground = true,
}: Props) => {
  const sectionClassName = clsx(
    styles.container,
    { [styles.backgroundOff]: !hasBackground },
    []
  );
  return (
    <section className={sectionClassName}>
      {title && <h2 className={styles.title}>{title}</h2>}
      {children}
    </section>
  );
};
