// PlaybookContent.tsx - Play mastery/knowledge tracking
// Shows which plays each player knows and their mastery level

import React, { useState, useEffect } from 'react';
import { Book, Star, Circle, ChevronDown, ChevronRight, Users } from 'lucide-react';
import { PlayerPortrait } from '../components';
import { useManagementStore, selectLeagueId, selectFranchiseId } from '../../../stores/managementStore';
import { managementApi } from '../../../api/managementClient';
import type { MasteryStatus, PlayerPlaybook as ApiPlayerPlaybook } from '../../../api/managementClient';

// === Local Types (adapted from API) ===

interface PlayMastery {
  playId: string;
  playName: string;
  status: MasteryStatus;
  reps: number;
}

interface PlayerPlaybook {
  id: string;
  name: string;
  position: string;
  depth: number;
  plays: PlayMastery[];
  learnedCount: number;
  masteredCount: number;
}

interface PlayInfo {
  id: string;
  name: string;
  category: string;
}

// === Helpers ===

const getMasteryIcon = (status: MasteryStatus) => {
  switch (status) {
    case 'mastered':
      return <Star size={14} className="mastery-icon mastery-icon--mastered" />;
    case 'learned':
      return <Circle size={14} className="mastery-icon mastery-icon--learned" />;
    case 'unlearned':
      return <Circle size={14} className="mastery-icon mastery-icon--unlearned" />;
  }
};

const getMasteryLabel = (status: MasteryStatus): string => {
  switch (status) {
    case 'mastered': return 'Mastered';
    case 'learned': return 'Learned';
    case 'unlearned': return 'Unlearned';
  }
};

const getRepsToNext = (status: MasteryStatus, reps: number): string => {
  if (status === 'mastered') return 'Max';
  if (status === 'learned') return `${Math.max(0, 40 - reps)} to master`;
  return `${Math.max(0, 15 - reps)} to learn`;
};

const getProgressPercent = (status: MasteryStatus, reps: number): number => {
  if (status === 'mastered') return 100;
  if (status === 'learned') return 50 + Math.min(50, (reps / 40) * 50);
  return Math.min(50, (reps / 15) * 50);
};

// Infer play category from play name/id
const inferCategory = (playId: string, playName: string): string => {
  const lower = playId.toLowerCase() + playName.toLowerCase();
  if (lower.includes('zone') || lower.includes('power') || lower.includes('counter') || lower.includes('draw') || lower.includes('stretch')) return 'run';
  if (lower.includes('rpo')) return 'rpo';
  if (lower.includes('pa') || lower.includes('play_action') || lower.includes('boot')) return 'pa';
  return 'passing';
};

// Category tag abbreviations
const CATEGORY_TAGS: Record<string, string> = {
  passing: 'PASS',
  run: 'RUN',
  rpo: 'RPO',
  pa: 'PA',
};

// Transform API data to local format
const transformApiData = (apiPlayers: ApiPlayerPlaybook[]): { players: PlayerPlaybook[]; plays: PlayInfo[] } => {
  const playMap = new Map<string, PlayInfo>();

  const players = apiPlayers.map((p, index) => {
    const plays = p.plays.map(play => {
      const category = inferCategory(play.play_id, play.play_name);
      if (!playMap.has(play.play_id)) {
        playMap.set(play.play_id, { id: play.play_id, name: play.play_name, category });
      }
      return {
        playId: play.play_id,
        playName: play.play_name,
        status: play.status,
        reps: play.reps,
      };
    });

    return {
      id: p.player_id,
      name: p.name,
      position: p.position,
      depth: p.depth ?? (index < 11 ? 1 : 2), // Assume first 11 are starters if depth not provided
      plays,
      learnedCount: p.learned_count,
      masteredCount: p.mastered_count,
    };
  });

  return { players, plays: Array.from(playMap.values()) };
};

// === Components ===

interface PlayerPlaybookCardProps {
  player: PlayerPlaybook;
  leagueId?: string;
  expanded: boolean;
  onToggle: () => void;
}

const PlayerPlaybookCard: React.FC<PlayerPlaybookCardProps> = ({ player, leagueId, expanded, onToggle }) => {
  const mastered = player.masteredCount;
  const learned = player.learnedCount;
  const unlearned = player.plays.length - mastered - learned;

  return (
    <div className={`playbook-card ${expanded ? 'playbook-card--expanded' : ''}`}>
      <button className="playbook-card__header" onClick={onToggle}>
        <div className="playbook-card__player">
          <PlayerPortrait
            playerId={player.id}
            leagueId={leagueId}
            size="roster"
          />
          <div className="playbook-card__info">
            <span className="playbook-card__name">{player.name}</span>
            <span className="playbook-card__pos">{player.position}</span>
          </div>
        </div>
        <div className="playbook-card__counts">
          <span className="playbook-card__count playbook-card__count--mastered" title="Mastered">
            <Star size={12} /> {mastered}
          </span>
          <span className="playbook-card__count playbook-card__count--learned" title="Learned">
            <Circle size={12} /> {learned}
          </span>
          <span className="playbook-card__count playbook-card__count--unlearned" title="Unlearned">
            <Circle size={12} /> {unlearned}
          </span>
        </div>
        {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </button>

      {expanded && (
        <div className="playbook-card__body">
          <div className="playbook-card__plays">
            {player.plays.map(play => (
              <div key={play.playId} className={`playbook-play playbook-play--${play.status}`}>
                <div className="playbook-play__header">
                  {getMasteryIcon(play.status)}
                  <span className="playbook-play__name">{play.playName}</span>
                  <span className="playbook-play__status">{getMasteryLabel(play.status)}</span>
                </div>
                <div className="playbook-play__progress">
                  <div className="playbook-play__bar">
                    <div
                      className="playbook-play__bar-fill"
                      style={{ width: `${getProgressPercent(play.status, play.reps)}%` }}
                    />
                  </div>
                  <span className="playbook-play__reps">
                    {play.reps} reps · {getRepsToNext(play.status, play.reps)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// === Play-centric view ===

interface PlayKnowledgeRowProps {
  play: PlayInfo;
  players: PlayerPlaybook[];
}

const PlayKnowledgeRow: React.FC<PlayKnowledgeRowProps> = ({ play, players }) => {
  const playersWithPlay = players
    .map(p => {
      const mastery = p.plays.find(pm => pm.playId === play.id);
      return mastery ? { player: p, mastery } : null;
    })
    .filter(Boolean) as { player: PlayerPlaybook; mastery: PlayMastery }[];

  // Split by starters (depth 1) vs backups (depth 2+)
  const starters = playersWithPlay.filter(p => p.player.depth === 1);
  const backups = playersWithPlay.filter(p => p.player.depth > 1);

  const startersMastered = starters.filter(p => p.mastery.status === 'mastered').length;
  const startersLearning = starters.filter(p => p.mastery.status === 'learned').length;
  const backupsMastered = backups.filter(p => p.mastery.status === 'mastered').length;
  const backupsLearning = backups.filter(p => p.mastery.status === 'learned').length;

  const tag = CATEGORY_TAGS[play.category] || play.category.toUpperCase();

  return (
    <div className="play-row">
      <div className="play-row__info">
        <span className={`play-row__tag play-row__tag--${play.category}`}>{tag}</span>
        <span className="play-row__name">{play.name}</span>
      </div>
      <div className="play-row__depth-stats">
        <div className="play-row__depth-group">
          <span className="play-row__stat play-row__stat--mastered">
            <Star size={10} /> {startersMastered}
          </span>
          <span className="play-row__stat play-row__stat--learning">
            <Circle size={10} /> {startersLearning}
          </span>
        </div>
        <div className="play-row__depth-group play-row__depth-group--backup">
          <span className="play-row__stat play-row__stat--mastered">
            <Star size={10} /> {backupsMastered}
          </span>
          <span className="play-row__stat play-row__stat--learning">
            <Circle size={10} /> {backupsLearning}
          </span>
        </div>
      </div>
    </div>
  );
};

// === Main Component ===

type ViewMode = 'players' | 'plays';

export const PlaybookContent: React.FC = () => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('players');
  const [players, setPlayers] = useState<PlayerPlaybook[]>([]);
  const [plays, setPlays] = useState<PlayInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const leagueId = useManagementStore(selectLeagueId);
  const franchiseId = useManagementStore(selectFranchiseId);

  useEffect(() => {
    if (!franchiseId) {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await managementApi.getPlaybookMastery(franchiseId);
        const { players: transformedPlayers, plays: transformedPlays } = transformApiData(data.players);
        setPlayers(transformedPlayers);
        setPlays(transformedPlays);
      } catch (err) {
        console.error('Failed to fetch playbook mastery:', err);
        setPlayers([]);
        setPlays([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [franchiseId]);

  if (loading) {
    return <div className="ref-content playbook-content">Loading...</div>;
  }

  return (
    <div className="ref-content playbook-content">
      {/* View Toggle */}
      <div className="playbook-content__header">
        <div className="playbook-content__toggle">
          <button
            className={`playbook-content__toggle-btn ${viewMode === 'players' ? 'playbook-content__toggle-btn--active' : ''}`}
            onClick={() => setViewMode('players')}
          >
            <Users size={14} /> By Player
          </button>
          <button
            className={`playbook-content__toggle-btn ${viewMode === 'plays' ? 'playbook-content__toggle-btn--active' : ''}`}
            onClick={() => setViewMode('plays')}
          >
            <Book size={14} /> By Play
          </button>
        </div>
      </div>

      {/* Player View */}
      {viewMode === 'players' && (
        <div className="playbook-content__list">
          {players.map(player => (
            <PlayerPlaybookCard
              key={player.id}
              player={player}
              leagueId={leagueId || undefined}
              expanded={expandedId === player.id}
              onToggle={() => setExpandedId(expandedId === player.id ? null : player.id)}
            />
          ))}
        </div>
      )}

      {/* Play View */}
      {viewMode === 'plays' && (
        <div className="playbook-content__plays">
          {/* Legend */}
          <div className="playbook-content__legend">
            <span className="playbook-content__legend-item">
              <Star size={10} className="playbook-content__legend-icon--mastered" /> Mastered
            </span>
            <span className="playbook-content__legend-item">
              <Circle size={10} className="playbook-content__legend-icon--learning" /> Learning
            </span>
          </div>
          {/* Column Headers */}
          <div className="playbook-content__plays-header">
            <span className="playbook-content__plays-header-label">Play</span>
            <div className="playbook-content__plays-header-groups">
              <span className="playbook-content__plays-header-depth">Starters</span>
              <span className="playbook-content__plays-header-depth playbook-content__plays-header-depth--backup">Backups</span>
            </div>
          </div>
          {plays.map(play => (
            <PlayKnowledgeRow key={play.id} play={play} players={players} />
          ))}
        </div>
      )}

      {players.length === 0 && !loading && (
        <div className="playbook-content__empty">
          <p>No playbook data available</p>
          <p className="playbook-content__hint">Play mastery will be tracked through practice sessions.</p>
        </div>
      )}
    </div>
  );
};

export default PlaybookContent;
