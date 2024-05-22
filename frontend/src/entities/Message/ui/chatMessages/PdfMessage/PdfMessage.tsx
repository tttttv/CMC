import { FileIcon } from "../../images/FileIcon";
import styles from "./PdfMessage.module.scss";
export const PdfMessage = () => {
  return (
    <div className={styles.pdf}>
      <FileIcon />
      <span>PDF файл</span>
    </div>
  );
};
