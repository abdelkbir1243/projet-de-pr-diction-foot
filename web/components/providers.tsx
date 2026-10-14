"use client";
import { ThemeProvider } from "next-themes";
import type { ReactNode } from "react";
import { I18nProvider } from "@/lib/i18n";
import { ClockContext } from "./live";

export function Providers({ children, fixedNow = null }: { children: ReactNode; fixedNow?: string | null }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <ClockContext.Provider value={fixedNow ? new Date(fixedNow).getTime() : null}>
        <I18nProvider>{children}</I18nProvider>
      </ClockContext.Provider>
    </ThemeProvider>
  );
}
