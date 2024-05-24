import { SVGProps } from "react";

export const UserIcon = (props: SVGProps<SVGSVGElement>) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width={40}
    height={40}
    fill="none"
    {...props}
  >
    <path
      fill="var(--accentColor)"
      d="M20 16.667a6.667 6.667 0 1 0 0-13.334 6.667 6.667 0 0 0 0 13.334ZM20 36.667c8.284 0 15-3.731 15-8.334C35 23.731 28.284 20 20 20c-8.284 0-15 3.731-15 8.333 0 4.603 6.716 8.334 15 8.334Z"
    />
  </svg>
);
