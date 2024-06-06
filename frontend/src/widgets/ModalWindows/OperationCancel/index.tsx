import Button from "$/shared/ui/kit/Button/Button";
import ButtonCancel from "$/shared/ui/kit/ButtonCancel/CancelButton";
import ModalWindow from "$/shared/ui/modals/ModalWindow";
import icon from "./icon.svg";
import styles from "./index.module.scss";

interface Props {
  confirmFn: () => void;
  closeFn: () => void;
  isPending: boolean;
  title?: string;
  buttonText?: string;
}
const OperationCancel = ({
  closeFn,
  confirmFn,
  isPending,
  title,
  buttonText,
}: Props) => {
  return (
    <ModalWindow icon={<img src={icon} alt="accept" />}>
      <h1 className={styles.modalTitle}>
        {title ?? "Эту операцию нельзя отменить"}
      </h1>
      <Button onClick={confirmFn} disabled={isPending}>
        {isPending ? "Подождите..." : buttonText ?? "Подтверждаю"}
      </Button>
      <ButtonCancel disabled={isPending} onClick={closeFn}>
        Отмена
      </ButtonCancel>
    </ModalWindow>
  );
};

export default OperationCancel;
