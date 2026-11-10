import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@/app/globals.css";
import { getPublicConfig } from "@/lib/env";

const config = getPublicConfig();

export const metadata: Metadata = {
  title: `${config.appName} — Engineering Foundation`,
  description:
    "AI-powered financial intelligence and equity research foundation for Indian (NSE, BSE) and US (NYSE, NASDAQ) markets.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#F6F7F9] text-slate-900 antialiased selection:bg-slate-900 selection:text-white">
        {children}
      </body>
    </html>
  );
}

