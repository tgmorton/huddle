/**
 * Ticker - Scrolling news feed at the bottom of the screen
 */

import React, { useRef, useEffect, useState } from 'react';
import { useManagementStore, selectTickerItems } from '../../stores/managementStore';
import type { TickerItem } from '../../types/management';
import './Ticker.css';

const TICKER_CATEGORY_COLORS: Record<string, string> = {
  SIGNING: '#10b981',
  RELEASE: '#ef4444',
  TRADE: '#3b82f6',
  WAIVER: '#6b7280',
  SCORE: '#fbbf24',
  INJURY: '#ef4444',
  INJURY_REPORT: '#f97316',
  SUSPENSION: '#dc2626',
  RETIREMENT: '#8b5cf6',
  HOLDOUT: '#f97316',
  DRAFT_PICK: '#10b981',
  DRAFT_TRADE: '#3b82f6',
  DEADLINE: '#fbbf24',
  RECORD: '#fbbf24',
  AWARD: '#fbbf24',
  RUMOR: '#6b7280',
};

export const Ticker: React.FC = () => {
  const items = useManagementStore(selectTickerItems);
  const containerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);

  // Auto-scroll animation
  useEffect(() => {
    if (!containerRef.current || !contentRef.current || isPaused) return;

    const container = containerRef.current;
    const content = contentRef.current;

    let animationId: number;
    let scrollPosition = 0;
    const scrollSpeed = 0.5; // pixels per frame

    const animate = () => {
      scrollPosition += scrollSpeed;

      // Reset when we've scrolled past the content
      if (scrollPosition >= content.scrollWidth / 2) {
        scrollPosition = 0;
      }

      container.scrollLeft = scrollPosition;
      animationId = requestAnimationFrame(animate);
    };

    animationId = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [items, isPaused]);

  if (items.length === 0) {
    return (
      <div className="ticker ticker--empty">
        <span className="ticker__empty-text">No news yet...</span>
      </div>
    );
  }

  // Duplicate items for seamless scrolling
  const displayItems = [...items, ...items];

  return (
    <div
      className="ticker"
      ref={containerRef}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="ticker__label">NEWS</div>
      <div className="ticker__content" ref={contentRef}>
        {displayItems.map((item, index) => (
          <TickerItemDisplay key={`${item.id}-${index}`} item={item} />
        ))}
      </div>
    </div>
  );
};

interface TickerItemDisplayProps {
  item: TickerItem;
}

const TickerItemDisplay: React.FC<TickerItemDisplayProps> = ({ item }) => {
  const color = TICKER_CATEGORY_COLORS[item.category] || '#6b7280';

  return (
    <div className={`ticker__item ${item.is_breaking ? 'breaking' : ''}`}>
      <span
        className="ticker__item-category"
        style={{ backgroundColor: color }}
      >
        {formatCategory(item.category)}
      </span>
      <span className="ticker__item-headline">{item.headline}</span>
      <span className="ticker__item-age">{item.age_display}</span>
      <span className="ticker__separator">•</span>
    </div>
  );
};

function formatCategory(category: string): string {
  return category.replace(/_/g, ' ');
}
