import styles from "./VideoMessage.module.scss";
export const VideoMessage = ({ base64 }: { base64: string }) => {
  return (
    <div className={styles.video}>
      <video src={base64}></video>
      <div className={styles.play}>
        <div className={styles.triangle}></div>
      </div>
    </div>
  );
};
