// CoachesContent.tsx - Coaching staff panel content

import React from 'react';

export const CoachesContent: React.FC = () => (
  <div className="ref-content">
    <div className="panel-section">
      <div className="panel-section__header">Coaching Staff</div>
      <div className="stat-table__row"><span className="stat-table__name">Bill Thompson</span><span className="stat-table__stat">HC</span></div>
      <div className="stat-table__row"><span className="stat-table__name">Mike Roberts</span><span className="stat-table__stat">OC</span></div>
      <div className="stat-table__row"><span className="stat-table__name">James Wilson</span><span className="stat-table__stat">DC</span></div>
    </div>
  </div>
);

export default CoachesContent;
