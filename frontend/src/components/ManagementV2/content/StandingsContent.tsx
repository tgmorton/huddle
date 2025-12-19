// StandingsContent.tsx - Division standings panel content

import React from 'react';

export const StandingsContent: React.FC = () => (
  <div className="ref-content">
    <div className="ref-content__group">
      <div className="ref-content__group-header">NFC East</div>
      <div className="ref-content__standing ref-content__standing--you">
        <span>1.</span><span>Your Team</span><span>3-1</span>
      </div>
      <div className="ref-content__standing">
        <span>2.</span><span>Dallas</span><span>3-1</span>
      </div>
      <div className="ref-content__standing">
        <span>3.</span><span>Philadelphia</span><span>2-2</span>
      </div>
      <div className="ref-content__standing">
        <span>4.</span><span>NY Giants</span><span>1-3</span>
      </div>
      <div className="ref-content__standing">
        <span>5.</span><span>Washington</span><span>1-3</span>
      </div>
    </div>
  </div>
);

export default StandingsContent;
