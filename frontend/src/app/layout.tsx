import type { Metadata } from 'next';
import '../index.css';

export const metadata: Metadata = {
  title: 'Medical Document Processing System',
  description: 'Medical document processing and MDT report generation system',
  icons: {
    icon: '/medical-icon.svg', 
  },
  viewport: 'width=device-width, initial-scale=1.0',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="overflow-x-hidden">
      <head>
        <meta charSet="UTF-8" />
        <link rel="icon" type="image/svg+xml" href="/medical-icon.svg" />
      </head>
      <body className="bg-gray-50 overflow-x-hidden max-w-[100vw]">
        <div id="root" className="overflow-x-hidden max-w-[100vw]">{children}</div>
      </body>
    </html>
  );
}