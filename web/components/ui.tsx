"use client";

import { cn } from "@/lib/cn";
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export function Button({
  children,
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  return (
    <button
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-control px-3 text-small",
        variant === "primary" && "bg-fg text-bg",
        variant === "ghost" && "border border-border bg-bg text-fg",
        variant === "danger" && "border border-bad text-bad",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-control border border-border bg-bg px-3 text-body text-fg",
        className,
      )}
      {...props}
    />
  );
}

export function Card({
  children,
  low,
  className,
  id,
}: {
  children: ReactNode;
  low?: boolean;
  className?: string;
  id?: string;
}) {
  return (
    <section
      id={id}
      className={cn(
        "rounded-card border border-border p-6",
        low ? "bg-wash" : "bg-bg",
        className,
      )}
    >
      {children}
    </section>
  );
}

export function Pill({ children, tone = "muted" }: { children: ReactNode; tone?: "muted" | "good" | "bad" }) {
  const cls =
    tone === "good" ? "text-good border-good" : tone === "bad" ? "text-bad border-bad" : "text-fg-3 border-border";
  return (
    <span className={cn("inline-flex h-6 items-center rounded-pill border px-2 text-caption", cls)}>
      {children}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-control bg-wash", className)} style={{ animationDuration: "1.2s" }} />;
}
