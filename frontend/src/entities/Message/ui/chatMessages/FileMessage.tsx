import { formatBase64Url } from "$/widgets/Chat/lib/base64";
import styles from "./FileMessage.module.scss";
import { PdfMessage } from "./PdfMessage/PdfMessage";
import { VideoMessage } from "./VideoMessage/VideoMessage";

interface Props {
  url: string;
  documentType: "video" | "image" | "pdf";
  altName?: string;
}
export const FileMessage = ({ url, documentType }: Props) => {
  const isVideo = documentType === "video";
  const isPDF = documentType === "pdf";

  if (isVideo) {
    return <VideoMessage base64={url} />;
  }

  if (isPDF) {
    return <PdfMessage />;
  }

  return <img className={styles.messageImage} src={formatBase64Url(url)} />;
};
