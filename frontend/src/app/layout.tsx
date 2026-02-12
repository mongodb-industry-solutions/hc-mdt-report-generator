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
    <html lang="en">
      <head>
        <meta charSet="UTF-8" />
        <link rel="icon" type="image/svg+xml" href="/medical-icon.svg" />
      </head>
      <body className="bg-gray-50">
        <div id="root">{children}</div>
      </body>
    </html>
  );
}