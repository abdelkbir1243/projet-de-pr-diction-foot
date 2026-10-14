"use client";
import * as T from "@radix-ui/react-tabs";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Onglets synchronisés avec l'URL (?tab=…) : liens partageables et bouton retour fonctionnel. */
export function UrlTabs({ tabs, defaultTab, children, className }: { tabs: { value: string; label: ReactNode }[]; defaultTab: string; children: ReactNode; className?: string }) {
  const sp = useSearchParams();
  const router = useRouter();
  const path = usePathname();
  const current = sp.get("tab") ?? defaultTab;
  return (
    <T.Root
      value={tabs.some((t) => t.value === current) ? current : defaultTab}
      onValueChange={(v) => {
        const q = new URLSearchParams(sp.toString());
        if (v === defaultTab) q.delete("tab"); else q.set("tab", v);
        router.replace(`${path}${q.size ? `?${q}` : ""}`, { scroll: false });
      }}
      className={className}
    >
      <T.List className="scrollbar-thin -mx-3 flex gap-1 overflow-x-auto border-b border-border px-3 sm:mx-0 sm:px-0" aria-label="Sections">
        {tabs.map((t) => (
          <T.Trigger
            key={t.value}
            value={t.value}
            className={cn(
              "relative shrink-0 px-3 py-2.5 text-[13px] font-medium text-text-3 transition-colors hover:text-text",
              "data-[state=active]:text-text data-[state=active]:after:absolute data-[state=active]:after:inset-x-2 data-[state=active]:after:-bottom-px data-[state=active]:after:h-0.5 data-[state=active]:after:rounded-full data-[state=active]:after:bg-brand",
            )}
          >
            {t.label}
          </T.Trigger>
        ))}
      </T.List>
      {children}
    </T.Root>
  );
}

export function TabPanel({ value, children, className }: { value: string; children: ReactNode; className?: string }) {
  return <T.Content value={value} className={cn("min-w-0 animate-fade-in pt-4 outline-none", className)}>{children}</T.Content>;
}
