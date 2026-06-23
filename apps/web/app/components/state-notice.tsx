import type { ReactNode } from "react";

type StateNoticeTone = "loading" | "empty" | "error" | "success" | "info";

export function StateNotice({
  tone = "info",
  title,
  children
}: {
  tone?: StateNoticeTone;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className={`state-notice state-notice-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <strong>{title}</strong>
      {children ? <p>{children}</p> : null}
    </div>
  );
}
