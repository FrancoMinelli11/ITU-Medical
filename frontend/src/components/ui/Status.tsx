import React from "react";

export type StatusTone = "green" | "blue" | "amber" | "gray";

export function Status({
  children,
  tone = "green",
}: {
  children: React.ReactNode;
  tone?: StatusTone;
}) {
  return (
    <span className={`status ${tone}`}>
      <i />
      {children}
    </span>
  );
}
