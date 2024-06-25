import { useQuery } from "@tanstack/react-query";
import { currencyAPI } from "../api/currency";

export const useCurrency = () => {
  const {
    data: fromValues,
    isLoading: isFromLoading,
    refetch: fromRefetch,
  } = useQuery({
    queryKey: ["fromValues"],
    queryFn: currencyAPI.getFromValues,
    select: (data) => data.data.methods,
  });
  const {
    data: toValues,
    isLoading: isToLoading,
    refetch: toRefetch,
  } = useQuery({
    queryKey: ["toValues"],
    queryFn: currencyAPI.getToValues,
    select: (data) => data.data.methods,
  });
  return {
    to: {
      loading: isToLoading,
      data: toValues,
      refetch: toRefetch,
    },
    from: {
      loading: isFromLoading,
      data: fromValues,
      refetch: fromRefetch,
    },
  };
};
