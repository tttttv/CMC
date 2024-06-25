import styles from "./OpenedDocument.module.scss";
import ReactPlayer from "react-player";

interface Props {
  url: string;
  documentType: "video" | "image" | "pdf";
  altName?: string;
}
export const OpenedDocument = ({ url, documentType, altName }: Props) => {
  const isVideo = documentType === "video";
  const isPdf = documentType === "pdf";

  if (isVideo) {
    return <ReactPlayer url={url} playing controls />;
  }
  if (isPdf) {
    return <embed src={url} type="application/pdf" className={styles.pdf} />;
  }

  return <img src={url} alt={altName} className={styles.image} />;
};
