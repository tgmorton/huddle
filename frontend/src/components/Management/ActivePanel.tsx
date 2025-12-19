/**
 * ActivePanel - Left side content panel that shows event details or other views
 */

import React from 'react';
import { useManagementStore } from '../../stores/managementStore';
import { PracticePanel } from './PracticePanel';
import { GameDayPanel } from './GameDayPanel';
import './ActivePanel.css';

interface PracticeAllocation {
  playbook: number;
  development: number;
  gamePrep: number;
}

interface ActivePanelProps {
  onGoBack: () => void;
  onRunPractice?: (eventId: string, allocation: PracticeAllocation) => void;
  onPlayGame?: (eventId: string) => void;
  onSimGame?: (eventId: string) => void;
}

export const ActivePanel: React.FC<ActivePanelProps> = ({
  onGoBack,
  onRunPractice,
  onPlayGame,
  onSimGame,
}) => {
  const clipboard = useManagementStore((state) => state.clipboard);
  const events = useManagementStore((state) => state.events);

  if (!clipboard) {
    return (
      <div className="active-panel active-panel--loading">
        <div className="active-panel__loader">Loading...</div>
      </div>
    );
  }

  const { panel } = clipboard;
  const canGoBack = panel.can_go_back;

  // If viewing an event detail
  if (panel.panel_type === 'EVENT_DETAIL' && panel.event_id) {
    const event = events?.pending.find((e) => e.id === panel.event_id);
    if (event) {
      // Special handling for practice events
      if (event.category === 'PRACTICE' && onRunPractice) {
        // Look for next game event to get opponent
        const nextGameEvent = events?.pending.find(e => e.category === 'GAME');
        const nextOpponent = nextGameEvent?.payload?.opponent_name as string | undefined;
        return (
          <div className="active-panel">
            {canGoBack && (
              <button className="active-panel__back-btn" onClick={onGoBack}>
                ← Back
              </button>
            )}
            <PracticePanel
              eventId={event.id}
              duration={event.payload?.duration_minutes as number ?? 120}
              nextOpponent={nextOpponent}
              onRunPractice={onRunPractice}
              onCancel={onGoBack}
            />
          </div>
        );
      }

      // Special handling for game events
      if (event.category === 'GAME' && onPlayGame && onSimGame) {
        return (
          <div className="active-panel">
            <GameDayPanel
              eventId={event.id}
              week={event.payload?.week as number ?? 1}
              opponentName={event.payload?.opponent_name as string ?? 'Opponent'}
              isHome={event.payload?.is_home as boolean ?? true}
              onPlayGame={onPlayGame}
              onSimGame={onSimGame}
              onCancel={onGoBack}
            />
          </div>
        );
      }

      return (
        <div className="active-panel">
          {canGoBack && (
            <button className="active-panel__back-btn" onClick={onGoBack}>
              ← Back
            </button>
          )}
          <EventDetailView event={event} />
        </div>
      );
    }
  }

  // Default welcome/dashboard view
  return (
    <div className="active-panel">
      <DashboardView />
    </div>
  );
};

interface EventDetailViewProps {
  event: {
    id: string;
    title: string;
    description: string;
    category: string;
    priority: string;
    deadline: string | null;
    payload: Record<string, unknown>;
  };
}

const EventDetailView: React.FC<EventDetailViewProps> = ({ event }) => {
  return (
    <div className="event-detail">
      <div className="event-detail__header">
        <span className="event-detail__category">{event.category}</span>
        <span className="event-detail__priority">{event.priority}</span>
      </div>

      <h2 className="event-detail__title">{event.title}</h2>
      <p className="event-detail__description">{event.description}</p>

      {event.deadline && (
        <div className="event-detail__deadline">
          <strong>Deadline:</strong> {new Date(event.deadline).toLocaleString()}
        </div>
      )}

      <div className="event-detail__content">
        {/* Event-specific content would go here */}
        <div className="event-detail__placeholder">
          <p>Event details and actions will appear here based on event type.</p>
          <p>This could include:</p>
          <ul>
            <li>Free agent signing interface</li>
            <li>Trade negotiation screen</li>
            <li>Practice drill selection</li>
            <li>Game preparation options</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

/**
 * WeekOverview - The hub of the weekly rhythm
 *
 * Design Philosophy:
 * - Weekly Loop is core: Monday review → Practice → Friday prep → Game Day
 * - Show what's at stake this week (opponent, standings implications)
 * - Surface decisions that need attention
 * - Feel the weight of the coming game
 */
interface ScheduleGame {
  game_id: string;
  week: number;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  is_played: boolean;
}

const WeekOverview: React.FC = () => {
  const calendar = useManagementStore((state) => state.calendar);
  const events = useManagementStore((state) => state.events);
  const [schedule, setSchedule] = React.useState<ScheduleGame[]>([]);
  const [teamRecord, setTeamRecord] = React.useState({ wins: 0, losses: 0 });

  const teamAbbr = 'PHI'; // TODO: Get from franchise state
  const currentWeek = calendar?.current_week ?? 1;

  // Fetch schedule on mount
  React.useEffect(() => {
    const fetchSchedule = async () => {
      try {
        const response = await fetch(`/api/v1/admin/schedule?team=${teamAbbr}`);
        if (response.ok) {
          const data = await response.json();
          setSchedule(data);

          // Calculate record from played games
          const record = data.reduce(
            (acc: { wins: number; losses: number }, game: ScheduleGame) => {
              if (!game.is_played) return acc;
              const isHome = game.home_team === teamAbbr;
              const ourScore = isHome ? game.home_score : game.away_score;
              const theirScore = isHome ? game.away_score : game.home_score;
              if (ourScore !== null && theirScore !== null) {
                if (ourScore > theirScore) acc.wins++;
                else if (ourScore < theirScore) acc.losses++;
              }
              return acc;
            },
            { wins: 0, losses: 0 }
          );
          setTeamRecord(record);
        }
      } catch (err) {
        // Silently fail - will show placeholder
      }
    };
    fetchSchedule();
  }, [teamAbbr]);

  // Find next unplayed game
  const nextGameData = schedule.find(g => !g.is_played && g.week >= currentWeek);
  const isHome = nextGameData ? nextGameData.home_team === teamAbbr : true;
  const opponent = nextGameData
    ? (isHome ? nextGameData.away_team : nextGameData.home_team)
    : null;

  const nextGame = {
    opponent: opponent || 'TBD',
    isHome,
    week: nextGameData?.week ?? currentWeek,
    day: 'Sunday',
    time: '1:00 PM',
    isDivision: false, // TODO: Determine from team data
    opponentRecord: '', // TODO: Fetch opponent record
  };

  // Determine what day of the week we're in
  const getDayContext = () => {
    const day = calendar?.day_name ?? 'Monday';
    switch (day) {
      case 'Monday':
        return { phase: 'Recovery', desc: 'Review last week, check injuries' };
      case 'Tuesday':
      case 'Wednesday':
      case 'Thursday':
        return { phase: 'Practice', desc: 'Prepare for Sunday' };
      case 'Friday':
        return { phase: 'Finalize', desc: 'Lock in gameplan and roster' };
      case 'Saturday':
        return { phase: 'Travel', desc: 'Final preparations' };
      case 'Sunday':
        return { phase: 'Game Day', desc: 'Time to compete' };
      default:
        return { phase: 'Preparation', desc: 'Focus on the week ahead' };
    }
  };

  const dayContext = getDayContext();

  // Practice schedule for the week
  const practiceSchedule = [
    { day: 'Mon', label: 'Recovery', active: calendar?.day_name === 'Monday', complete: false },
    { day: 'Tue', label: 'Practice', active: calendar?.day_name === 'Tuesday', complete: false },
    { day: 'Wed', label: 'Practice', active: calendar?.day_name === 'Wednesday', complete: false },
    { day: 'Thu', label: 'Practice', active: calendar?.day_name === 'Thursday', complete: false },
    { day: 'Fri', label: 'Walkthrough', active: calendar?.day_name === 'Friday', complete: false },
    { day: 'Sat', label: 'Travel', active: calendar?.day_name === 'Saturday', complete: false },
    { day: 'Sun', label: 'Game', active: calendar?.day_name === 'Sunday', complete: false },
  ];

  return (
    <div className="week-overview">
      {/* Header - Current Position */}
      <div className="week-overview__header">
        <div className="week-overview__title-section">
          <h1 className="week-overview__title">{calendar?.week_display ?? 'Week 1'}</h1>
          <div className="week-overview__record">
            {teamRecord.wins}-{teamRecord.losses}
          </div>
        </div>
        <div className="week-overview__phase">
          <span className="week-overview__phase-name">{dayContext.phase}</span>
          <span className="week-overview__phase-desc">{dayContext.desc}</span>
        </div>
      </div>

      {/* Next Game Card */}
      <div className="week-overview__game-card">
        <div className="week-overview__game-header">
          <span className="week-overview__game-label">Next Game</span>
          <span className="week-overview__game-tags">
            {nextGame.isDivision && <span className="week-overview__tag week-overview__tag--division">Division</span>}
          </span>
        </div>
        <div className="week-overview__game-matchup">
          <span className="week-overview__game-venue">{nextGame.isHome ? 'vs' : '@'}</span>
          <span className="week-overview__game-opponent">{nextGame.opponent}</span>
          <span className="week-overview__game-opp-record">({nextGame.opponentRecord})</span>
        </div>
        <div className="week-overview__game-when">
          {nextGame.day} • {nextGame.time}
        </div>
      </div>

      {/* Week Timeline */}
      <div className="week-overview__timeline">
        <div className="week-overview__timeline-header">This Week</div>
        <div className="week-overview__timeline-days">
          {practiceSchedule.map((day, idx) => (
            <div
              key={day.day}
              className={`week-overview__day ${day.active ? 'week-overview__day--active' : ''} ${day.complete ? 'week-overview__day--complete' : ''}`}
            >
              <div className="week-overview__day-name">{day.day}</div>
              <div className="week-overview__day-label">{day.label}</div>
              {idx < practiceSchedule.length - 1 && <div className="week-overview__day-connector" />}
            </div>
          ))}
        </div>
      </div>

      {/* Attention Needed */}
      {events && events.pending.length > 0 && (
        <div className="week-overview__attention">
          <div className="week-overview__attention-header">
            <span className="week-overview__attention-title">Needs Attention</span>
            <span className="week-overview__attention-count">{events.pending.length}</span>
          </div>
          <div className="week-overview__attention-list">
            {events.pending.slice(0, 3).map((event) => (
              <div key={event.id} className="week-overview__attention-item">
                <span className={`week-overview__attention-dot week-overview__attention-dot--${event.priority.toLowerCase()}`} />
                <span className="week-overview__attention-text">{event.title}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions Hint */}
      <div className="week-overview__hint">
        Use the <strong>Roster</strong> and <strong>Depth Chart</strong> tabs to prepare for Sunday.
        Events will appear as time progresses.
      </div>
    </div>
  );
};

// Keep DashboardView as alias for backwards compatibility
const DashboardView = WeekOverview;
