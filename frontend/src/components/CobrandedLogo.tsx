import React from 'react';

interface MongoDBHealthcareLogoProps {
  /**
   * Size variant for the logo
   * - sm: Small (height: 32px)
   * - md: Medium (height: 40px) - default
   * - lg: Large (height: 56px)
   * - xl: Extra Large (height: 72px)
   */
  size?: 'sm' | 'md' | 'lg' | 'xl';

  /**
   * Custom className for additional styling
   */
  className?: string;
}

const MongoDBHealthcareLogo: React.FC<MongoDBHealthcareLogoProps> = ({
  size = 'md',
  className = ''
}) => {
  // Height mapping for different sizes
  const sizeMap = {
    sm: 32,
    md: 40,
    lg: 56,
    xl: 72
  };

  const height = sizeMap[size];
  const logoWidth = height * (720/140);

  return (
    <div className={className} style={{ height: `${height}px` }}>
      <svg
        width={logoWidth}
        height={height}
        viewBox="0 0 720 140"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label="MongoDB Healthcare"
      >
        <title>MongoDB Healthcare</title>
        {/* MongoDB Leaf Icon */}
        <g transform="translate(8,12)">
          <path d="M26 114 C18 86, 18 58, 28 36 C38 16, 54 6, 66 4 C58 18, 52 36, 50 52 C48 70, 52 90, 62 114 Z" fill="#00ED64" />
          <path d="M58 28 C56 54, 58 92, 66 116" stroke="#8CEBB0" strokeWidth="4" fill="none" strokeLinecap="round" />
        </g>
        {/* MongoDB Text */}
        <g fontFamily="Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" fontWeight="800" fontSize="40">
          <text x="110" y="68" fill="#FFFFFF">MongoDB</text>
        </g>
        {/* Healthcare Text */}
        <g fontFamily="Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" fontWeight="700" fontSize="34">
          <text x="110" y="120" fill="#00ED64">MDT Report Generator</text>
        </g>
      </svg>
    </div>
  );
};

export default MongoDBHealthcareLogo;