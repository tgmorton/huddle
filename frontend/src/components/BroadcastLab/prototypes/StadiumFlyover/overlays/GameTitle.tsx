/**
 * GameTitle.tsx - HTML overlay for network branding and matchup info
 * Styled like real TV broadcast graphics
 */

import { useRef, useEffect } from 'react';
import gsap from 'gsap';
import type { TeamColors } from '../scene/Field';

export type NetworkStyle = 'nbc' | 'cbs' | 'espn' | 'fox';

interface GameTitleProps {
  homeTeam: TeamColors;
  awayTeam: TeamColors;
  network: NetworkStyle;
  gameTime: string;
  isVisible: boolean;
}

const NETWORK_STYLES: Record<
  NetworkStyle,
  { logo: string; bgColor: string; accentColor: string; font: string }
> = {
  nbc: {
    logo: 'NBC',
    bgColor: 'rgba(0, 0, 0, 0.85)',
    accentColor: '#FFD700',
    font: "'Helvetica Neue', sans-serif",
  },
  cbs: {
    logo: 'CBS',
    bgColor: 'rgba(0, 40, 85, 0.9)',
    accentColor: '#FFFFFF',
    font: "'Arial Black', sans-serif",
  },
  espn: {
    logo: 'ESPN',
    bgColor: 'rgba(205, 33, 42, 0.9)',
    accentColor: '#FFFFFF',
    font: "'Impact', sans-serif",
  },
  fox: {
    logo: 'FOX',
    bgColor: 'rgba(0, 0, 0, 0.85)',
    accentColor: '#00A1E4',
    font: "'Helvetica Neue', sans-serif",
  },
};

export function GameTitle({
  homeTeam,
  awayTeam,
  network,
  gameTime,
  isVisible,
}: GameTitleProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const style = NETWORK_STYLES[network];

  // Animate in/out
  useEffect(() => {
    if (!containerRef.current) return;

    if (isVisible) {
      gsap.fromTo(
        containerRef.current,
        { opacity: 0, y: 50 },
        { opacity: 1, y: 0, duration: 0.6, delay: 0.3, ease: 'power2.out' }
      );
    } else {
      gsap.to(containerRef.current, {
        opacity: 0,
        y: -30,
        duration: 0.3,
        ease: 'power2.in',
      });
    }
  }, [isVisible]);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'absolute',
        bottom: '80px',
        left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '12px',
        fontFamily: style.font,
        opacity: 0,
        pointerEvents: 'none',
      }}
    >
      {/* Network bug */}
      <div
        style={{
          padding: '8px 20px',
          background: style.bgColor,
          borderRadius: '4px',
          color: style.accentColor,
          fontSize: '14px',
          fontWeight: 'bold',
          letterSpacing: '2px',
        }}
      >
        {style.logo} SPORTS
      </div>

      {/* Main matchup card */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '20px',
          padding: '16px 32px',
          background: style.bgColor,
          borderRadius: '8px',
          border: `2px solid ${style.accentColor}`,
        }}
      >
        {/* Away team */}
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              width: '60px',
              height: '60px',
              borderRadius: '50%',
              background: awayTeam.primary,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '8px',
              border: `3px solid ${awayTeam.secondary}`,
            }}
          >
            <span
              style={{
                color: awayTeam.secondary,
                fontSize: '18px',
                fontWeight: 'bold',
              }}
            >
              {awayTeam.abbreviation}
            </span>
          </div>
          <div style={{ color: '#ffffff', fontSize: '16px', fontWeight: 'bold' }}>
            {awayTeam.name}
          </div>
        </div>

        {/* VS */}
        <div
          style={{
            color: style.accentColor,
            fontSize: '24px',
            fontWeight: 'bold',
            padding: '0 10px',
          }}
        >
          @
        </div>

        {/* Home team */}
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              width: '60px',
              height: '60px',
              borderRadius: '50%',
              background: homeTeam.primary,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '8px',
              border: `3px solid ${homeTeam.secondary}`,
            }}
          >
            <span
              style={{
                color: homeTeam.secondary,
                fontSize: '18px',
                fontWeight: 'bold',
              }}
            >
              {homeTeam.abbreviation}
            </span>
          </div>
          <div style={{ color: '#ffffff', fontSize: '16px', fontWeight: 'bold' }}>
            {homeTeam.name}
          </div>
        </div>
      </div>

      {/* Game time */}
      <div
        style={{
          padding: '6px 16px',
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '4px',
          color: '#ffffff',
          fontSize: '14px',
        }}
      >
        {gameTime}
      </div>
    </div>
  );
}
