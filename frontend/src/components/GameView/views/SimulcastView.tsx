/**
 * SimulcastView - Rich game information display
 *
 * Split layout:
 * - TOP: Large field visualization showing drive progress
 * - BOTTOM: Two columns (Formation + situation | Drive play-by-play)
 */

import React from 'react';
import type { GameSituation, PlayResult, Formation, PersonnelGroup, DrivePlay } from '../types';
import { ResultOverlay } from '../components/ResultOverlay';
import { DriveFieldView } from '../components/DriveFieldView';
import { FormationDiagram } from '../components/FormationDiagram';

interface SimulcastViewProps {
  situation: GameSituation | null;
  lastResult: PlayResult | null;
  showResult: boolean;
  formation: Formation | null;
  personnel: PersonnelGroup;
  userOnOffense: boolean;
  possessionHome?: boolean;
  currentDrive?: DrivePlay[];
  driveStartLos?: number;
  homeTeamColor?: string;
  awayTeamColor?: string;
  homeTeamLogo?: string;
  homeTeam?: string;
  awayTeam?: string;
  onDismissResult?: () => void;
}

export const SimulcastView: React.FC<SimulcastViewProps> = ({
  situation,
  lastResult,
  showResult,
  formation,
  personnel,
  userOnOffense,
  possessionHome,
  currentDrive = [],
  driveStartLos,
  homeTeamColor,
  awayTeamColor,
  homeTeamLogo,
  homeTeam,
  awayTeam,
  onDismissResult,
}) => {
  if (!situation) {
    return (
      <div className="simulcast-view simulcast-view--loading">
        <p>Loading game state...</p>
      </div>
    );
  }

  // Use first play's LOS or current LOS as drive start
  const effectiveDriveStart = driveStartLos ??
    (currentDrive.length > 0 ? currentDrive[0].los : situation.los);

  // Calculate drive stats
  const driveStats = {
    plays: currentDrive.length,
    yards: currentDrive.reduce((sum, p) => sum + p.yardsGained, 0),
    firstDowns: currentDrive.filter(p => p.isFirstDown).length,
  };

  // Determine field direction based on possession and half
  // In 1st half (Q1-Q2): Home team drives right, Away drives left
  // In 2nd half (Q3-Q4): Teams switch ends, so directions flip
  const isSecondHalf = (situation.quarter || 1) >= 3;
  const homeDirection: 'right' | 'left' = isSecondHalf ? 'left' : 'right';
  const fieldDirection: 'right' | 'left' = possessionHome
    ? homeDirection
    : (homeDirection === 'right' ? 'left' : 'right');

  return (
    <div className="simulcast-view">
      {/* TOP: Large field visualization */}
      <div className="simulcast-view__field-section">
        {/* Possession indicator */}
        <div className="simulcast-view__possession">
          <span className={`simulcast-view__possession-team ${possessionHome ? 'active' : ''}`} style={{ color: homeTeamColor }}>
            {possessionHome && '● '}{homeTeam || 'HOME'}
          </span>
          <span className="simulcast-view__possession-label">BALL</span>
          <span className={`simulcast-view__possession-team ${!possessionHome ? 'active' : ''}`} style={{ color: awayTeamColor }}>
            {awayTeam || 'AWAY'}{!possessionHome && ' ●'}
          </span>
        </div>
        <DriveFieldView
          los={situation.los}
          driveStartLos={effectiveDriveStart}
          firstDownLine={Math.min(100, situation.los + situation.distance)}
          currentDrive={currentDrive}
          isRedZone={situation.isRedZone}
          direction={fieldDirection}
          offenseTeamColor={possessionHome ? homeTeamColor : awayTeamColor}
          defenseTeamColor={possessionHome ? awayTeamColor : homeTeamColor}
          homeTeamLogo={homeTeamLogo}
          offenseTeam={possessionHome ? homeTeam : awayTeam}
          defenseTeam={possessionHome ? awayTeam : homeTeam}
        />
      </div>

      {/* BOTTOM: Two-column content */}
      <div className="simulcast-view__content">
        {/* Left: Formation + Situation */}
        <div className="simulcast-view__formation-area">
          <div className="simulcast-view__formation-wrapper">
            <FormationDiagram
              formation={formation || 'shotgun'}
              personnel={personnel}
              isOffense={userOnOffense}
              showLabels={true}
              size="large"
            />
          </div>

          {/* Down and distance badge */}
          <div className={`simulcast-view__down-badge ${situation.down === 4 ? 'simulcast-view__down-badge--fourth' : ''}`}>
            <span className="simulcast-view__down">{getOrdinal(situation.down)}</span>
            <span className="simulcast-view__distance">
              {situation.isGoalToGo ? '& GOAL' : `& ${situation.distance}`}
            </span>
            <span className="simulcast-view__location">{situation.yardLineDisplay}</span>
          </div>
        </div>

        {/* Right: Drive Progress */}
        <div className="simulcast-view__drive-area">
          <div className="simulcast-view__drive-header">THIS DRIVE</div>

          {currentDrive.length === 0 ? (
            <div className="simulcast-view__drive-empty">
              <span>Drive starting...</span>
            </div>
          ) : (
            <div className="simulcast-view__drive-plays">
              {currentDrive.slice(-6).map((play, index) => (
                <div
                  key={index}
                  className={`simulcast-view__drive-play ${play.isFirstDown ? 'simulcast-view__drive-play--first-down' : ''}`}
                >
                  <span className="simulcast-view__drive-play-down">
                    {getOrdinal(play.down).toLowerCase()}
                  </span>
                  <span className="simulcast-view__drive-play-name">
                    {play.playName || play.playType}
                  </span>
                  <span className={`simulcast-view__drive-play-yards ${getYardsClass(play.yardsGained, play.outcome)}`}>
                    {formatYards(play.yardsGained, play.outcome)}
                  </span>
                  {play.isFirstDown && (
                    <span className="simulcast-view__drive-play-first">1ST</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Drive summary */}
          <div className="simulcast-view__drive-summary">
            <span className="simulcast-view__drive-stat">
              <strong>{driveStats.plays}</strong> plays
            </span>
            <span className="simulcast-view__drive-stat">
              <strong className={driveStats.yards >= 0 ? 'positive' : 'negative'}>
                {driveStats.yards >= 0 ? '+' : ''}{driveStats.yards}
              </strong> yards
            </span>
            {driveStats.firstDowns > 0 && (
              <span className="simulcast-view__drive-stat">
                <strong>{driveStats.firstDowns}</strong> first down{driveStats.firstDowns > 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Last play banner */}
      {!showResult && lastResult && (
        <div className={`simulcast-view__last-play ${getLastPlayClass(lastResult)}`}>
          <span className="simulcast-view__last-play-label">LAST PLAY:</span>
          <span className="simulcast-view__last-play-desc">{lastResult.description}</span>
          {lastResult.yardsGained !== 0 && (
            <span className={`simulcast-view__last-play-yards ${lastResult.yardsGained > 0 ? 'positive' : 'negative'}`}>
              {lastResult.yardsGained > 0 ? '+' : ''}{lastResult.yardsGained} yds
            </span>
          )}
          {lastResult.firstDown && <span className="simulcast-view__last-play-badge">FIRST DOWN</span>}
          {lastResult.touchdown && <span className="simulcast-view__last-play-badge simulcast-view__last-play-badge--td">TOUCHDOWN!</span>}
          {lastResult.turnover && <span className="simulcast-view__last-play-badge simulcast-view__last-play-badge--turnover">TURNOVER</span>}
        </div>
      )}

      {/* Result overlay */}
      {showResult && lastResult && (
        <ResultOverlay
          result={lastResult}
          onDismiss={onDismissResult}
        />
      )}
    </div>
  );
};

function getOrdinal(n: number): string {
  if (n === 1) return '1ST';
  if (n === 2) return '2ND';
  if (n === 3) return '3RD';
  return '4TH';
}

function formatYards(yards: number, outcome: string): string {
  if (outcome === 'incomplete') return 'INC';
  if (outcome === 'sack') return `${yards}`;
  if (yards === 0) return '0';
  return yards > 0 ? `+${yards}` : `${yards}`;
}

function getYardsClass(yards: number, outcome: string): string {
  if (outcome === 'incomplete') return 'neutral';
  if (outcome === 'sack') return 'negative';
  if (yards > 0) return 'positive';
  if (yards < 0) return 'negative';
  return 'neutral';
}

function getLastPlayClass(result: PlayResult): string {
  if (result.touchdown) return 'simulcast-view__last-play--touchdown';
  if (result.turnover) return 'simulcast-view__last-play--turnover';
  if (result.firstDown) return 'simulcast-view__last-play--first-down';
  if (result.yardsGained > 0) return 'simulcast-view__last-play--positive';
  if (result.yardsGained < 0 || result.outcome === 'sack') return 'simulcast-view__last-play--negative';
  return '';
}

export default SimulcastView;
