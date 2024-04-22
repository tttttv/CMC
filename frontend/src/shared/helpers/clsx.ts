type Modes = Record<string, boolean>;
const clsx = (baseClass: string, modes: Modes, additions: string[]) => {
  return [
    baseClass,
    ...additions,
    ...Object.entries(modes)
      .filter(([, include]) => include)
      .map(([className]) => className),
  ].join(" ");
};

export default clsx;