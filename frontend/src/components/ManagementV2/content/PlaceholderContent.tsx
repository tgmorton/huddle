// PlaceholderContent.tsx - Placeholder for panels not yet built

import React from 'react';

interface PlaceholderContentProps {
  title: string;
}

export const PlaceholderContent: React.FC<PlaceholderContentProps> = ({ title }) => (
  <div className="ref-content">
    <div className="placeholder-content">
      <span className="placeholder-content__title">{title}</span>
      <span className="placeholder-content__subtitle">Coming soon</span>
    </div>
  </div>
);

export default PlaceholderContent;
