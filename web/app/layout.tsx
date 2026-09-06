"use client";

import { StartBanner } from "@/components/StartBanner";
import "@/styles/globals.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient());
  return (
    <html lang="en">
      <body>
        <QueryClientProvider client={client}>
          <StartBanner />
          {children}
        </QueryClientProvider>
      </body>
    </html>
  );
}
