import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AegisGate | AI Execution Proxy & Pluggable Harness",
  description: "Enterprise DevOps & AI Gatekeeper Platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var saved = localStorage.getItem('aegisgate-theme');
                  if (saved === 'dark') {
                    document.documentElement.classList.add('dark');
                  } else {
                    document.documentElement.classList.remove('dark');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="bg-slate-950 text-slate-100 h-full overflow-hidden antialiased">
        {children}
      </body>
    </html>
  );
}
