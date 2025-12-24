// NewsPane.tsx - News item pane (reference type - no header, no footer)

import React from 'react';

interface NewsPaneProps {
  title: string;
  content: string;
  onComplete: () => void;
}

export const NewsPane: React.FC<NewsPaneProps> = ({ content }) => (
  <div className="pane pane--no-header">
    <div className="pane__body">
      <p className="pane__text">{content}</p>
    </div>
  </div>
);

export default NewsPane;
