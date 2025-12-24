// WeekPanel.tsx - Week Journal view showing accumulated effects of decisions

import React, { useState, useCallback, useEffect } from 'react';
import { Play, FastForward, Star } from 'lucide-react';
import { managementApi } from '../../../api/managementClient';
import type { WeekJournalEntry, JournalCategory } from '../../../api/managementClient';
import { useManagementStore, selectJournalVersion } from '../../../stores/managementStore';
import type { ManagementEvent } from '../../../types/management';

interface WeekPanelProps {
  franchiseId?: string | null;
}

const CATEGORY_CONFIG: Record<JournalCategory, { abbr: string; label: string }> = {
  practice: { abbr: 'PRC', label: 'Practice' },
  conversation: { abbr: 'MTG', label: 'Meeting' },
  intel: { abbr: 'INT', label: 'Intel' },
  injury: { abbr: 'INJ', label: 'Injury' },
  transaction: { abbr: 'TXN', label: 'Transaction' },
};

const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const DAY_ABBRS = ['M', 'Tu', 'W', 'Th', 'F', 'Sa', 'Su'];


// Group entries by day, most recent first within each day
const groupByDay = (entries: WeekJournalEntry[], currentDay: number): Map<number, WeekJournalEntry[]> => {
  const groups = new Map<number, WeekJournalEntry[]>();

  // Initialize groups for days up to current
  for (let i = currentDay; i >= 0; i--) {
    groups.set(i, []);
  }

  for (const entry of entries) {
    const existing = groups.get(entry.day) || [];
    // Prepend new entries so most recent appears first
    groups.set(entry.day, [entry, ...existing]);
  }

  return groups;
};

export const WeekPanel: React.FC<WeekPanelProps> = ({ franchiseId }) => {
  const [advancing, setAdvancing] = useState(false);
  const [entries, setEntries] = useState<WeekJournalEntry[]>([]);
  const [weekNumber, setWeekNumber] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  // Get calendar state from store
  const calendar = useManagementStore(state => state.calendar);
  const journalVersion = useManagementStore(selectJournalVersion);
  const updateCalendar = useManagementStore(state => state.updateCalendar);
  const setEvents = useManagementStore(state => state.setEvents);

  // Extract current day from calendar (0-6, where 0=Monday)
  const currentWeek = weekNumber ?? calendar?.current_week ?? 1;

  // Get day of week from current_date (if available)
  const currentDayIndex = calendar?.current_date
    ? new Date(calendar.current_date).getDay()
    : 2; // Default: Tuesday (NFL week start)

  // Convert JS day (0=Sun) to our day (0=Mon)
  const dayIndex = currentDayIndex === 0 ? 6 : currentDayIndex - 1;

  // Opponent info (will be populated when we have schedule data)
  const opponent = calendar ? {
    name: 'TBD',
    abbr: 'TBD',
    isHome: true,
    record: '',
  } : null;

  // Fetch week journal data
  useEffect(() => {
    if (!franchiseId) return;

    const fetchJournal = async () => {
      setLoading(true);
      try {
        const data = await managementApi.getWeekJournal(franchiseId);
        setWeekNumber(data.week);
        setEntries(data.entries);
      } catch (err) {
        console.error('Failed to fetch week journal:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchJournal();
  }, [franchiseId]);

  // Refetch when journalVersion changes (triggered by panes posting to journal)
  useEffect(() => {
    if (!franchiseId || journalVersion === 0) return;

    const fetchJournal = async () => {
      try {
        const data = await managementApi.getWeekJournal(franchiseId);
        setWeekNumber(data.week);
        setEntries(data.entries);
      } catch (err) {
        console.error('Failed to fetch week journal:', err);
      }
    };

    fetchJournal();
  }, [franchiseId, journalVersion]);

  // Use actual entries only
  const displayEntries = entries;

  // Group entries by day (most recent first)
  const groupedEntries = groupByDay(displayEntries, dayIndex);
  const dayKeys = Array.from(groupedEntries.keys()).sort((a, b) => b - a);

  // Refetch journal after state changes
  const refetchJournal = useCallback(async () => {
    if (!franchiseId) return;
    try {
      const data = await managementApi.getWeekJournal(franchiseId);
      setWeekNumber(data.week);
      setEntries(data.entries);
    } catch (err) {
      console.error('Failed to fetch week journal:', err);
    }
  }, [franchiseId]);

  const handleAdvanceDay = useCallback(async () => {
    if (!franchiseId || advancing) return;
    setAdvancing(true);
    try {
      const response = await managementApi.advanceDay(franchiseId);

      // Update store with new calendar state
      updateCalendar(response.calendar as any);

      // Convert API events to ManagementEvent format and update store
      const events = response.day_events.map(e => ({
        ...e,
        created_at: new Date(e.created_at).toISOString(),
      })) as ManagementEvent[];
      setEvents(events);

      await refetchJournal();
    } catch (err) {
      console.error('Failed to advance day:', err);
    } finally {
      setAdvancing(false);
    }
  }, [franchiseId, advancing, refetchJournal, updateCalendar, setEvents]);

  const handleAdvanceToGame = useCallback(async () => {
    if (!franchiseId || advancing) return;
    setAdvancing(true);
    try {
      await managementApi.advanceToGame(franchiseId);
      await refetchJournal();
    } catch (err) {
      console.error('Failed to advance to game:', err);
    } finally {
      setAdvancing(false);
    }
  }, [franchiseId, advancing, refetchJournal]);

  return (
    <div className="week-panel">
      {/* Compact Header */}
      <div className="week-panel__header">
        <span className="week-panel__title">Week {currentWeek}</span>
        {opponent && (
          <>
            <span className="week-panel__sep">·</span>
            <span className="week-panel__opponent">
              {opponent.isHome ? 'vs' : '@'} {opponent.name}{opponent.record && ` (${opponent.record})`}
            </span>
          </>
        )}
      </div>

      {/* Horizontal Timeline */}
      <div className="week-panel__timeline">
        <div className="week-panel__timeline-days">
          {DAY_ABBRS.map((day, i) => (
            <div
              key={i}
              className={`week-panel__timeline-day ${i < dayIndex ? 'complete' : ''} ${i === dayIndex ? 'current' : ''} ${i === 6 ? 'gameday' : ''}`}
            >
              {i === 6 ? <Star size={10} /> : day}
            </div>
          ))}
        </div>
        <div className="week-panel__timeline-track">
          <div
            className="week-panel__timeline-progress"
            style={{ width: `${((dayIndex + 1) / 7) * 100}%` }}
          />
        </div>
      </div>

      {/* Activities Timeline (DeskDrawer style) */}
      <div className="week-panel__activities">
        {loading ? (
          <div className="week-panel__empty">Loading...</div>
        ) : displayEntries.length === 0 ? (
          <div className="week-panel__empty">
            <p>No activities yet</p>
            <p className="week-panel__hint">Activities will appear as you progress through the week.</p>
          </div>
        ) : (
          <div className="week-panel__activities-timeline">
            {dayKeys.map((day) => {
              const dayEntries = groupedEntries.get(day) || [];
              const isToday = day === dayIndex;
              const dayLabel = isToday ? 'Today' : DAY_NAMES[day];

              return (
                <div key={day} className="week-panel__day-group">
                  {/* Day marker */}
                  <div className="week-panel__day-row">
                    <div className="week-panel__day-marker">
                      <div className={`week-panel__day-dot ${isToday ? 'week-panel__day-dot--today' : ''}`} />
                    </div>
                    <span className="week-panel__day-label">{dayLabel}</span>
                  </div>

                  {/* Entries for this day */}
                  {dayEntries.length > 0 && (
                    <div className="week-panel__entries">
                      {dayEntries.map(entry => {
                        const config = CATEGORY_CONFIG[entry.category];
                        return (
                          <div key={entry.id} className="week-panel__entry-wrapper">
                            <div className={`week-panel__entry week-panel__entry--${entry.category}`}>
                              <span className="week-panel__entry-abbr" data-category={entry.category}>
                                {config.abbr}
                              </span>
                              <div className="week-panel__entry-info">
                                <span className="week-panel__entry-title">{entry.title}</span>
                                {entry.player && (
                                  <span className="week-panel__entry-subtitle">
                                    {entry.player.position} · {entry.player.name}
                                  </span>
                                )}
                              </div>
                            </div>
                            {/* Effect note with amber border */}
                            {entry.effect && (
                              <div className="week-panel__entry-effect">
                                <div className="week-panel__effect-line" />
                                <span className="week-panel__effect-text">{entry.effect}</span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="week-panel__actions">
        <button
          className="week-panel__btn week-panel__btn--advance"
          onClick={handleAdvanceDay}
          disabled={advancing || dayIndex >= 6}
        >
          <Play size={14} />
          <span>Advance Day</span>
        </button>
        <button
          className="week-panel__btn week-panel__btn--skip"
          onClick={handleAdvanceToGame}
          disabled={advancing || dayIndex >= 6}
        >
          <FastForward size={14} />
          <span>To Game</span>
        </button>
      </div>
    </div>
  );
};

export default WeekPanel;
