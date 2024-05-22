import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import styles from "./index.module.scss";
import { ErrorBoundary } from "$/pages/Root/ui/ErrorBoundary";

// eslint-disable-next-line react-refresh/only-export-components
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});
const Wrapper = ({ children }: { children: React.ReactNode }) => {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <div className={styles.wrapper}>{children}</div>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};

export default Wrapper;
