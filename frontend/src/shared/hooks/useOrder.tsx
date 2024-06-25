import { useQuery } from "@tanstack/react-query";
import { orderAPI } from "../api/order";

export const useOrder = () => {
  const { data, isLoading } = useQuery({
    queryKey: ["order"],
    queryFn: orderAPI.getOrderState,
    select: (data) => data.data,
  });
  return { data, isLoading };
};
