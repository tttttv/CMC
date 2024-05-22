import styles from "./index.module.scss";

interface Props {
  checked: boolean;
  label: string;
  setChecked: (checked: boolean) => void;
}
const Checkbox = ({ checked, label, setChecked }: Props) => {
  return (
    <div className={styles.checkboxContainer}>
      <div className={styles.checkbox} aria-hidden>
        <div className={styles.checkmark}>
          <svg
            width="9"
            height="7"
            viewBox="0 0 9 7"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M0.875001 3L3.26893 5.39393C3.32751 5.45251 3.42249 5.45251 3.48107 5.39393L8.375 0.5"
              stroke="var(--accentColor)"
              strokeWidth="1.2"
            />
          </svg>
        </div>
      </div>
      <input
        type="checkbox"
        className={styles.checkbox}
        defaultChecked={checked}
        checked={checked}
        id={label}
        onChange={(e) => setChecked(e.target.checked)}
      />
      <label className={styles.label} htmlFor={label}>
        {label}
      </label>
    </div>
  );
};
export default Checkbox;
