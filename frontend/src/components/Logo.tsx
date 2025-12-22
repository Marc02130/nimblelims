import React, { useMemo } from 'react';
import { SvgIcon, SvgIconProps } from '@mui/material';

const Logo: React.FC<SvgIconProps> = (props) => {
  // Generate unique ID for gradient to avoid conflicts when multiple logos are rendered
  const gradientId = useMemo(() => `nimbleGrad-${Math.random().toString(36).substr(2, 9)}`, []);

  return (
    <SvgIcon {...props} viewBox="0 0 64 64">
      <defs>
        <linearGradient id={gradientId} x1="100%" y1="100%" x2="0%" y2="0%">
          <stop offset="0%" style={{ stopColor: '#11998e', stopOpacity: 1 }} />
          <stop offset="100%" style={{ stopColor: '#38ef7d', stopOpacity: 1 }} />
        </linearGradient>
      </defs>
      <title>Apex Leap Abstract</title>
      <desc>A minimalist abstract form of a human figure at the highest point of a leap, suggesting weightlessness.</desc>
      <circle fill={`url(#${gradientId})`} cx="32" cy="12" r="7" />
      <path
        fill={`url(#${gradientId})`}
        d="M32,24.2c-3.9,4.5-9.1,10.1-16.3,16.3c-4.5,3.9-7.9,8.3-9.8,13c-0.8,1.9-0.3,3.2,1.1,4.2 c1.9,1.3,4.6,1.2,7.1-0.5c3.3-2.3,6.2-5.9,8.7-9.7C26.5,41.8,32,32,32,32s5.5,9.8,9.2,15.5c2.5,3.8,5.4,7.5,8.7,9.7 c2.5,1.7,5.2,1.8,7.1,0.5c1.4-0.9,1.9-2.3,1.1-4.2c-1.9-4.6-5.3-9-9.8-13C41.1,34.3,35.9,28.7,32,24.2z"
      />
    </SvgIcon>
  );
};

export default Logo;

