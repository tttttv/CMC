interface Props {
  rate: number;
  paymentName: string;
  withdrawName: string;
}

export const Course = ({ rate, paymentName, withdrawName }: Props) => {
  if (rate > 1)
    return (
      <>
        {rate.toFixed(2)} {paymentName} = 1 {withdrawName}
      </>
    );
  else {
    return (
      <>
        1 {paymentName} = {(1 / rate).toFixed(2)} {withdrawName}
      </>
    );
  }
};
