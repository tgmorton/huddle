// ScheduleContent.tsx - Season schedule panel content

import React from 'react';

export const ScheduleContent: React.FC = () => (
  <div className="ref-content">
    <div className="ref-content__stat-row">
      <span className="ref-content__stat">Week 5</span>
      <span className="ref-content__stat-label">of 17</span>
    </div>
    <div className="ref-content__group">
      <div className="ref-content__schedule-item ref-content__schedule-item--past">
        <span>W1</span><span>vs NYG</span><span className="ref-content__result--win">W 24-17</span>
      </div>
      <div className="ref-content__schedule-item ref-content__schedule-item--past">
        <span>W2</span><span>@ PHI</span><span className="ref-content__result--loss">L 14-21</span>
      </div>
      <div className="ref-content__schedule-item ref-content__schedule-item--past">
        <span>W3</span><span>vs WAS</span><span className="ref-content__result--win">W 31-20</span>
      </div>
      <div className="ref-content__schedule-item ref-content__schedule-item--past">
        <span>W4</span><span>@ CHI</span><span className="ref-content__result--win">W 28-14</span>
      </div>
      <div className="ref-content__schedule-item ref-content__schedule-item--current">
        <span>W5</span><span>vs DAL</span><span>Sunday</span>
      </div>
    </div>
  </div>
);

export default ScheduleContent;
