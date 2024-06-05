import { useCurrency } from "$/shared/hooks/useCurrency";
import List from "./List";

interface Props {
  changingProperty: "sending" | "getting";
}
export const CryptoList = ({ changingProperty }: Props) => {
  const { to, from } = useCurrency();

  const currency =
    changingProperty === "sending" ? from?.data?.crypto : to?.data?.crypto;

  return <List items={currency} changingProperty={changingProperty} />;
};
