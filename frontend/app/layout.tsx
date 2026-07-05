import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Foresight — Revenue Intelligence",
  description:
    "Real-time anomaly detection and AI-explained revenue alerts for SaaS founders.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
