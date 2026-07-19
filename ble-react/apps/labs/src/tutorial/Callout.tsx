import type { ReactNode } from "react";

export function Callout({
  variant = "info",
  title,
  children,
}: {
  variant?: "info" | "warn" | "tip";
  title?: string;
  children: ReactNode;
}) {
  return (
    <div className={`callout ${variant}`}>
      {title ? <strong className="title">{title}</strong> : null}
      {children}
    </div>
  );
}
