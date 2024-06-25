import { useQuery } from "@tanstack/react-query";
import { orderAPI } from "../api/order";

export const useMessages = () => {
  const { data, isLoading } = useQuery({
    queryKey: ["messages"],
    queryFn: orderAPI.getOrderMessages,
    retry: 0,
    select: (data) => data.data,
  });

  return { data, isLoading };
};
