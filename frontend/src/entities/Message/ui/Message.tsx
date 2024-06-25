import { useState } from "react";

import { formatBase64Url } from "../lib/base64";

import clsx from "$/shared/helpers/clsx";
import { Message as MessageType } from "$/shared/types/api/enitites";
import Modal from "$/shared/ui/modals/Modal";
import styles from "./Message.module.scss";
import { OpenedImage } from "./OpenedImage/OpenedImage";

import { FileMessage } from "./chatMessages/FileMessage";
import { UserIcon } from "./images/UserIcon";
import { generateImageName } from "../lib/image";

interface Props {
  message: MessageType;
}

export const Message = ({ message }: Props) => {
  const [openedImage, setOpenedImage] = useState<OpenedImage | undefined>();
  const isSupport = message.side === "SUPPORT";
  const messageContainerClassName = clsx(
    styles.messageContainer,
    { [styles.support]: isSupport },
    []
  );

  let documentType: "video" | "image" | "pdf" = "image";
  const isVideo = message.file?.includes("data:video");
  const isPdf = message.file?.includes("data:application/pdf");

  if (isVideo) {
    documentType = "video";
  } else if (isPdf) {
    documentType = "pdf";
  }

  return (
    <div className={messageContainerClassName}>
      <div className={styles.left}>
        {!isSupport ? (
          <UserIcon />
        ) : (
          <div className={styles.supportIcon}>T</div>
        )}
      </div>
      <div className={styles.message}>
        <div className={styles.messageHeader}>
          <h3 className={styles.nickName}>{message.nick_name}</h3>
          <span className={styles.time}>
            {message.dt?.split(" ")[1]?.slice(0, -3)}
          </span>
        </div>
        <p className={styles.messageText}>
          {!message.file ? (
            message.text
          ) : (
            <>
              {documentType === "pdf" ? (
                <a
                  className={styles.link}
                  href={message.file}
                  download={generateImageName(message.file)}
                >
                  <FileMessage
                    url={message.file}
                    documentType={documentType}
                  />
                </a>
              ) : (
                <button
                  onClick={() => {
                    setOpenedImage({
                      url: formatBase64Url(message.file),
                      name: message.nick_name[0],
                      datetime: message.dt,
                    });
                  }}
                >
                  <FileMessage
                    url={message.file}
                    documentType={documentType}
                  />
                </button>
              )}
            </>
          )}
        </p>
      </div>
      <Modal opened={openedImage !== undefined}>
        <OpenedImage
          url={openedImage?.url || ""}
          name={openedImage?.name || ""}
          datetime={openedImage?.datetime || ""}
          resetImageUrl={() => setOpenedImage(undefined)}
          documentType={documentType}
        />
      </Modal>
    </div>
  );
};
