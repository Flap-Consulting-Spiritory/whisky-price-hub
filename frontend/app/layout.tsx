import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PriceCheck",
  description: "Enrich your Spiritory KPI CSV with WhiskyBase price data",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground font-sans antialiased">
        <nav className="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-50">
          <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
            <a href="/" className="flex items-center gap-2.5">
              <span className="text-accent font-bold text-lg tracking-tight">
                Price<span className="text-foreground">Check</span>
              </span>
            </a>
            <span className="text-xs text-muted-foreground">
              WhiskyBase price enrichment
            </span>
          </div>
        </nav>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
