import { useQuery } from "@tanstack/react-query";
import { orderAPI } from "../api/order";
const REFETCH_DELAY = 10000;
export const useOrder = () => {
  const { data, isLoading } = useQuery({
    queryKey: ["order"],
    queryFn: orderAPI.getOrderState,
    select: (data) => data.data,
    retry: 0,
    refetchInterval: REFETCH_DELAY,
  });
  return { data, isLoading };
};
