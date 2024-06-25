import { getGradient } from "$/shared/helpers/getGradient";

export const Arrow = () => {
  const color = getComputedStyle(document.body).getPropertyValue(
    "--accentColor"
  );
  const gradient = getGradient(color);
  return (
    <svg
      data-name="divider-currency"
      width="64"
      height="24"
      viewBox="0 0 64 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <linearGradient id="paint0_linear_2_3329">
        <stop stop-color="var(--accentColor)" />
        <stop offset="0.277375" stop-color={gradient[3]} />
        <stop offset="0.591531" stop-color={gradient[2]} />
        <stop offset="1" stop-color={gradient[1]} />
      </linearGradient>
      <rect
        x="0.5"
        y="11.5"
        width="65"
        height="0.1"
        stroke="url(#paint0_linear_2_3329)"
        stroke-dasharray="2 2"
      />

      <rect
        x="0.5"
        y="11"
        width="65"
        height="0.1"
        stroke="url(#paint0_linear_2_3329)"
        stroke-dasharray="2 2"
      />
      <rect
        x="0.5"
        y="12"
        width="65"
        height="0.1"
        stroke="url(#paint0_linear_2_3329)"
        stroke-dasharray="2 2"
      />

      <rect
        x="20"
        y="24"
        width="24"
        height="24"
        rx="12"
        transform="rotate(-90 20 24)"
        fill="var(--accentColor)"
      />
      <path
        d="M38 12L38.5762 12.4801L38.9763 12L38.5762 11.5198L38 12ZM26 11.25C25.5858 11.25 25.25 11.5858 25.25 12C25.25 12.4142 25.5858 12.75 26 12.75L26 11.25ZM34.5762 17.2801L38.5762 12.4801L37.4238 11.5198L33.4238 16.3198L34.5762 17.2801ZM38.5762 11.5198L34.5762 6.71985L33.4238 7.68013L37.4238 12.4801L38.5762 11.5198ZM38 11.25L26 11.25L26 12.75L38 12.75L38 11.25Z"
        fill="white"
      />
      <defs></defs>
    </svg>
  );
};
