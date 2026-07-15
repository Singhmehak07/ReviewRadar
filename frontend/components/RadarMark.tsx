type RadarMarkProps = {
  size?: number;
};

export function RadarMark({ size = 32 }: RadarMarkProps) {
  return (
    <svg
      aria-hidden="true"
      className="radar-mark"
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
    >
      <circle cx="16" cy="16" r="13.5" stroke="currentColor" strokeWidth="1.5" opacity="0.45" />
      <circle cx="16" cy="16" r="8" stroke="currentColor" strokeWidth="1.5" opacity="0.32" />
      <path d="M16 16 24.5 6.5A13.5 13.5 0 0 1 29 16H16Z" fill="currentColor" opacity="0.18" />
      <path d="M16 16 24.5 6.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="16" cy="16" r="2.2" fill="currentColor" />
      <circle cx="22.5" cy="18.5" r="1.8" fill="currentColor" />
    </svg>
  );
}
