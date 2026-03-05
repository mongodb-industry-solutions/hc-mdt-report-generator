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
        
        <defs>
          <filter id="textShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="4" floodOpacity="0.8" floodColor="#000000"/>
          </filter>
          <filter id="iconShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="1" stdDeviation="3" floodOpacity="0.6" floodColor="#000000"/>
          </filter>
        </defs>
        
        {/* Hospital Icon */}
        <g transform="translate(8, 10)">
          <image href="/General_INDUSTRY_Hospital_inverse3x.png" width="100" height="100" filter="url(#iconShadow)"/>
        </g>
        
        {/* MongoDB Text */}
        <g fontFamily="Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" fontWeight="700" fontSize="38">
          <text x="140" y="65" fill="#FFFFFF" filter="url(#textShadow)" letterSpacing="0.5px">MongoDB Healthcare</text>
        </g>
        
        {/* Healthcare Text */}
        <g fontFamily="Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial" fontWeight="500" fontSize="26">
          <text x="140" y="105" fill="#00ED64" letterSpacing="1px" opacity="0.95" filter="url(#textShadow)">AI-Powered Medical Report Generator</text>
        </g>
      </svg>
    </div>
  );
};

export default MongoDBHealthcareLogo;