import { Fiat } from "../types/api/enitites";

export const useBanks = (currency: Fiat[] | undefined, type?: string) => {
  const banks =
    type === "all"
      ? currency?.map((bank) => bank.payment_methods).flat()
      : currency?.find((bank) => bank.id === type)?.payment_methods;
  return banks;
};
