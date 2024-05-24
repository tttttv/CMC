import { useEffect, useState } from "react";

const useMediaQuery = (query: string) => {
  const [isMatch, setIsMatch] = useState(false);
  useEffect(() => {
    const list = window.matchMedia(query);
    setIsMatch(list.matches);
    const onChange = (e: MediaQueryListEvent) => setIsMatch(e.matches);
    list.addEventListener("change", onChange);
    return () => list.removeEventListener("change", onChange);
  }, [query]);
  return { matching: isMatch };
};

export default useMediaQuery;
