import type { Metadata } from "next";
import "./globals.css";
import { ChatSidebar } from "@/components/ChatSidebar";

export const metadata: Metadata = {
  title: "KRAKEN — Captain's Bridge",
  description:
    "KRAKEN: federated SQL over every system you run, powered by Coral. One query to rule them all.",
  icons: {
    icon: "/favicon.ico",
  },
};

interface RootLayoutProps {
  children: React.ReactNode;
}

/**
 * Root layout.
 *
 * Structure:
 *   ┌──────────────────────────────────────────────────┐
 *   │  top nav                                         │
 *   ├─────────────────────────────┬────────────────────┤
 *   │  main content (flex-1)      │  chat sidebar      │
 *   └─────────────────────────────┴────────────────────┘
 *
 * ChatSidebar is a Client Component that mounts CopilotKit.
 * Everything else is a Server Component.
 */
export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full flex flex-col bg-[var(--color-surface)] text-[var(--color-text-primary)]">
        {/* ── Top navigation ─────────────────────────────── */}
        <header className="shrink-0 border-b border-[var(--color-border)] px-6 py-3 flex items-center gap-4">
          <span className="text-[var(--color-coral)] font-bold text-xl tracking-tight select-none">
            KRAKEN
          </span>
          <nav className="flex items-center gap-6 text-sm text-[var(--color-text-muted)]">
            <a
              href="/"
              className="hover:text-[var(--color-text-primary)] transition-colors"
            >
              Captain&apos;s Bridge
            </a>
            <a
              href="/spyglass"
              className="hover:text-[var(--color-text-primary)] transition-colors"
            >
              Spyglass
            </a>
            <a
              href="/reef-map"
              className="hover:text-[var(--color-text-primary)] transition-colors"
            >
              Reef Map
            </a>
          </nav>
        </header>

        {/* ── Page + sidebar ─────────────────────────────── */}
        <div className="flex flex-1 overflow-hidden">
          <main className="flex-1 overflow-y-auto">{children}</main>
          <ChatSidebar />
        </div>
      </body>
    </html>
  );
}
