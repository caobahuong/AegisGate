import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AegisGate | AI Execution Proxy & Pluggable Harness",
  description: "Enterprise DevOps & AI Gatekeeper Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}

