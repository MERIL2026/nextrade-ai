import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium tracking-tight transition-colors",
  {
    variants: {
      variant: {
        neutral: "border-slate-200 bg-slate-100 text-slate-700",
        healthy: "border-emerald-200 bg-emerald-50 text-emerald-800",
        degraded: "border-amber-200 bg-amber-50 text-amber-800",
        unhealthy: "border-rose-200 bg-rose-50 text-rose-800",
        ink: "border-slate-700 bg-slate-800 text-slate-100",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  },
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

