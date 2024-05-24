import { useQuery } from "@tanstack/react-query";
import { currencyAPI } from "../api/currency";

export const useCurrency = () => {
  const { data: fromValues } = useQuery({
    queryKey: ["fromValues"],
    queryFn: currencyAPI.getFromValues,
    select: (data) => data.data.methods,
  });
  const { data: toValues } = useQuery({
    queryKey: ["toValues"],
    queryFn: currencyAPI.getToValues,
    select: (data) => data.data.methods,
  });
  return {
    to: {
      data: toValues,
    },
    from: {
      data: fromValues,
    },
  };
};
