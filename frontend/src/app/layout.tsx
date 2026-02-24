import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth-context";
import { Header } from "@/app/header";
import "./globals.css";

export const metadata: Metadata = {
  title: "LearnerOS",
  description: "Adaptive learning platform powered by AI",
  icons: {
    icon: "/icon.png",
    apple: "/apple-icon.png",
    shortcut: "/favicon.ico",
  },
  openGraph: {
    title: "LearnerOS",
    description: "Adaptive learning platform powered by AI",
    images: ["/opengraph-image.png"],
  },
  twitter: {
    card: "summary_large_image",
    title: "LearnerOS",
    description: "Adaptive learning platform powered by AI",
    images: ["/opengraph-image.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AuthProvider>
          <div className="noise-overlay" />
          <div className="blur-circle blur-top-right" />
          <div className="blur-circle blur-bottom-left" />

          <div className="layout-container">
            <Header />
            <main className="main-content">
              {children}
            </main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
