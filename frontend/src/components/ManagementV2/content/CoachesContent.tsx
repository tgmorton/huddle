// CoachesContent.tsx - Coaching staff panel with grouped display and detail views

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Maximize2, Star, TrendingUp, TrendingDown, Minus } from 'lucide-react';

// === Types ===

type CoachRole =
  | 'HC'   // Head Coach
  | 'OC'   // Offensive Coordinator
  | 'DC'   // Defensive Coordinator
  | 'STC'  // Special Teams Coordinator
  | 'QB'   // QB Coach
  | 'RB'   // RB Coach
  | 'WR'   // WR Coach
  | 'TE'   // TE Coach
  | 'OL'   // OL Coach
  | 'DL'   // DL Coach
  | 'LB'   // LB Coach
  | 'DB'   // DB Coach
  | 'ST';  // Special Teams Coach

type SchemeType =
  | 'west_coast' | 'air_raid' | 'spread' | 'pro_style' | 'power_run' | 'zone_run'  // Offense
  | 'cover_2' | 'cover_3' | 'man_press' | 'zone_blitz' | '4-3' | '3-4';            // Defense

interface Coach {
  id: string;
  name: string;
  role: CoachRole;
  rating: number;           // 1-100
  experience: number;       // Years as coach
  age: number;
  scheme?: SchemeType;
  specialty?: string;       // e.g., "Player Development", "Game Planning"
  contractYears: number;
  salary: number;           // In thousands
  trend: 'up' | 'down' | 'stable';
  traits: string[];
}

type CoachView = { type: 'list' } | { type: 'coach'; coachId: string };

// === Demo Data ===

const DEMO_COACHES: Coach[] = [
  // Head Coach
  {
    id: 'hc-1',
    name: 'Bill Thompson',
    role: 'HC',
    rating: 82,
    experience: 15,
    age: 58,
    scheme: 'west_coast',
    specialty: 'Game Management',
    contractYears: 3,
    salary: 8500,
    trend: 'stable',
    traits: ['Motivator', 'Disciplinarian', 'Media Savvy'],
  },
  // Coordinators
  {
    id: 'oc-1',
    name: 'Mike Roberts',
    role: 'OC',
    rating: 78,
    experience: 12,
    age: 45,
    scheme: 'spread',
    specialty: 'Play Calling',
    contractYears: 2,
    salary: 2500,
    trend: 'up',
    traits: ['Aggressive', 'Innovative', 'QB Developer'],
  },
  {
    id: 'dc-1',
    name: 'James Wilson',
    role: 'DC',
    rating: 85,
    experience: 18,
    age: 52,
    scheme: 'cover_3',
    specialty: 'Pressure Packages',
    contractYears: 4,
    salary: 3000,
    trend: 'stable',
    traits: ['Blitz Heavy', 'Turnover Focused', 'Veteran Mentor'],
  },
  {
    id: 'stc-1',
    name: 'Carlos Martinez',
    role: 'STC',
    rating: 71,
    experience: 8,
    age: 41,
    specialty: 'Return Game',
    contractYears: 1,
    salary: 800,
    trend: 'down',
    traits: ['Detail Oriented', 'Special Teams Ace'],
  },
  // Offensive Position Coaches
  {
    id: 'qb-1',
    name: 'Dan Miller',
    role: 'QB',
    rating: 76,
    experience: 10,
    age: 48,
    specialty: 'Mechanics',
    contractYears: 2,
    salary: 1200,
    trend: 'up',
    traits: ['Former Player', 'Film Junkie'],
  },
  {
    id: 'rb-1',
    name: 'Marcus Johnson',
    role: 'RB',
    rating: 72,
    experience: 6,
    age: 38,
    specialty: 'Vision Training',
    contractYears: 2,
    salary: 600,
    trend: 'stable',
    traits: ['Young Coach', 'Player Connect'],
  },
  {
    id: 'wr-1',
    name: 'Terrell Davis',
    role: 'WR',
    rating: 80,
    experience: 9,
    age: 42,
    specialty: 'Route Running',
    contractYears: 3,
    salary: 900,
    trend: 'up',
    traits: ['Elite Developer', 'Technical Expert'],
  },
  {
    id: 'te-1',
    name: 'Greg Olsen Jr.',
    role: 'TE',
    rating: 68,
    experience: 4,
    age: 35,
    specialty: 'Blocking',
    contractYears: 1,
    salary: 450,
    trend: 'up',
    traits: ['Rising Star', 'Dual Threat Focus'],
  },
  {
    id: 'ol-1',
    name: 'Bob Patterson',
    role: 'OL',
    rating: 74,
    experience: 14,
    age: 55,
    scheme: 'zone_run',
    specialty: 'Pass Protection',
    contractYears: 2,
    salary: 800,
    trend: 'stable',
    traits: ['Old School', 'Technique Master'],
  },
  // Defensive Position Coaches
  {
    id: 'dl-1',
    name: 'Jerome Brown',
    role: 'DL',
    rating: 77,
    experience: 11,
    age: 46,
    specialty: 'Pass Rush',
    contractYears: 3,
    salary: 950,
    trend: 'stable',
    traits: ['Former All-Pro', 'Hands Technique'],
  },
  {
    id: 'lb-1',
    name: 'Ray Lewis III',
    role: 'LB',
    rating: 81,
    experience: 8,
    age: 40,
    specialty: 'Coverage',
    contractYears: 2,
    salary: 1100,
    trend: 'up',
    traits: ['Intensity', 'Film Study', 'Leadership'],
  },
  {
    id: 'db-1',
    name: 'Deion Sanders Jr.',
    role: 'DB',
    rating: 79,
    experience: 7,
    age: 37,
    specialty: 'Ball Skills',
    contractYears: 2,
    salary: 1000,
    trend: 'stable',
    traits: ['Swagger', 'Press Coverage', 'Turnover Creator'],
  },
];

const ROLE_LABELS: Record<CoachRole, string> = {
  HC: 'Head Coach',
  OC: 'Offensive Coordinator',
  DC: 'Defensive Coordinator',
  STC: 'Special Teams Coordinator',
  QB: 'Quarterbacks Coach',
  RB: 'Running Backs Coach',
  WR: 'Wide Receivers Coach',
  TE: 'Tight Ends Coach',
  OL: 'Offensive Line Coach',
  DL: 'Defensive Line Coach',
  LB: 'Linebackers Coach',
  DB: 'Defensive Backs Coach',
  ST: 'Special Teams Coach',
};

const SCHEME_LABELS: Record<SchemeType, string> = {
  west_coast: 'West Coast',
  air_raid: 'Air Raid',
  spread: 'Spread',
  pro_style: 'Pro Style',
  power_run: 'Power Run',
  zone_run: 'Zone Run',
  cover_2: 'Cover 2',
  cover_3: 'Cover 3',
  man_press: 'Man Press',
  zone_blitz: 'Zone Blitz',
  '4-3': '4-3 Base',
  '3-4': '3-4 Base',
};

// === Helpers ===

const getRatingColor = (rating: number): string => {
  if (rating >= 85) return 'var(--success)';
  if (rating >= 75) return 'var(--accent)';
  if (rating >= 65) return 'var(--text-secondary)';
  return 'var(--text-muted)';
};

const getRatingLabel = (rating: number): string => {
  if (rating >= 90) return 'Elite';
  if (rating >= 80) return 'Great';
  if (rating >= 70) return 'Good';
  if (rating >= 60) return 'Average';
  return 'Below Avg';
};

const getContractColor = (years: number): string => {
  if (years >= 3) return 'var(--text-secondary)';
  if (years === 2) return 'var(--accent)';
  return 'var(--danger)';
};

const formatSalary = (salary: number): string => {
  if (salary >= 1000) return `$${(salary / 1000).toFixed(1)}M`;
  return `$${salary}K`;
};

// === Components ===

interface CoachRowProps {
  coach: Coach;
  onClick: () => void;
  onPopOut?: () => void;
}

const CoachRow: React.FC<CoachRowProps> = ({ coach, onClick, onPopOut }) => {
  const TrendIcon = coach.trend === 'up' ? TrendingUp : coach.trend === 'down' ? TrendingDown : Minus;
  const trendColor = coach.trend === 'up' ? 'var(--success)' : coach.trend === 'down' ? 'var(--danger)' : 'var(--text-muted)';

  return (
    <tr className="coaches-table__row" onClick={onClick}>
      <td className="coaches-table__name">
        <div className="coaches-table__name-cell">
          <span className="coaches-table__coach-name">{coach.name}</span>
          {coach.rating >= 80 && <Star size={12} className="coaches-table__star" />}
        </div>
      </td>
      <td className="coaches-table__rating" style={{ color: getRatingColor(coach.rating) }}>
        {coach.rating}
      </td>
      <td className="coaches-table__exp">{coach.experience}y</td>
      <td className="coaches-table__scheme">
        {coach.scheme ? SCHEME_LABELS[coach.scheme] : coach.specialty || '—'}
      </td>
      <td className="coaches-table__contract" style={{ color: getContractColor(coach.contractYears) }}>
        {coach.contractYears}yr
      </td>
      <td className="coaches-table__salary">{formatSalary(coach.salary)}</td>
      <td className="coaches-table__trend">
        <TrendIcon size={14} style={{ color: trendColor }} />
      </td>
      <td className="coaches-table__action">
        <button
          className="coaches-table__popout"
          onClick={(e) => {
            e.stopPropagation();
            onPopOut?.();
          }}
        >
          <Maximize2 size={14} />
        </button>
      </td>
    </tr>
  );
};

interface CoachDetailProps {
  coach: Coach;
  onBack: () => void;
}

const CoachDetail: React.FC<CoachDetailProps> = ({ coach, onBack }) => {
  const TrendIcon = coach.trend === 'up' ? TrendingUp : coach.trend === 'down' ? TrendingDown : Minus;
  const trendColor = coach.trend === 'up' ? 'var(--success)' : coach.trend === 'down' ? 'var(--danger)' : 'var(--text-muted)';

  return (
    <div className="coach-detail">
      <button className="coach-detail__back" onClick={onBack}>
        &larr; Back to Staff
      </button>

      <div className="coach-detail__header">
        <div className="coach-detail__avatar">
          {coach.name.split(' ').map(n => n[0]).join('')}
        </div>
        <div className="coach-detail__info">
          <h2 className="coach-detail__name">{coach.name}</h2>
          <div className="coach-detail__role">{ROLE_LABELS[coach.role]}</div>
        </div>
        <div className="coach-detail__rating" style={{ color: getRatingColor(coach.rating) }}>
          <span className="coach-detail__rating-value">{coach.rating}</span>
          <span className="coach-detail__rating-label">{getRatingLabel(coach.rating)}</span>
        </div>
      </div>

      <div className="coach-detail__sections">
        {/* Bio Section */}
        <div className="coach-detail__section">
          <div className="coach-detail__section-header">Profile</div>
          <div className="coach-detail__stats">
            <div className="coach-detail__stat">
              <span className="coach-detail__stat-label">Age</span>
              <span className="coach-detail__stat-value">{coach.age}</span>
            </div>
            <div className="coach-detail__stat">
              <span className="coach-detail__stat-label">Experience</span>
              <span className="coach-detail__stat-value">{coach.experience} years</span>
            </div>
            <div className="coach-detail__stat">
              <span className="coach-detail__stat-label">Trend</span>
              <span className="coach-detail__stat-value" style={{ color: trendColor }}>
                <TrendIcon size={14} style={{ marginRight: 4 }} />
                {coach.trend === 'up' ? 'Rising' : coach.trend === 'down' ? 'Declining' : 'Stable'}
              </span>
            </div>
          </div>
        </div>

        {/* Scheme/Specialty Section */}
        <div className="coach-detail__section">
          <div className="coach-detail__section-header">Expertise</div>
          <div className="coach-detail__stats">
            {coach.scheme && (
              <div className="coach-detail__stat">
                <span className="coach-detail__stat-label">Scheme</span>
                <span className="coach-detail__stat-value">{SCHEME_LABELS[coach.scheme]}</span>
              </div>
            )}
            {coach.specialty && (
              <div className="coach-detail__stat">
                <span className="coach-detail__stat-label">Specialty</span>
                <span className="coach-detail__stat-value">{coach.specialty}</span>
              </div>
            )}
          </div>
        </div>

        {/* Traits Section */}
        <div className="coach-detail__section">
          <div className="coach-detail__section-header">Traits</div>
          <div className="coach-detail__traits">
            {coach.traits.map(trait => (
              <span key={trait} className="coach-detail__trait">{trait}</span>
            ))}
          </div>
        </div>

        {/* Contract Section */}
        <div className="coach-detail__section">
          <div className="coach-detail__section-header">Contract</div>
          <div className="coach-detail__stats">
            <div className="coach-detail__stat">
              <span className="coach-detail__stat-label">Years Remaining</span>
              <span className="coach-detail__stat-value" style={{ color: getContractColor(coach.contractYears) }}>
                {coach.contractYears} year{coach.contractYears !== 1 ? 's' : ''}
              </span>
            </div>
            <div className="coach-detail__stat">
              <span className="coach-detail__stat-label">Salary</span>
              <span className="coach-detail__stat-value">{formatSalary(coach.salary)}</span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="coach-detail__actions">
          <button className="coach-detail__btn coach-detail__btn--secondary">
            Extend Contract
          </button>
          <button className="coach-detail__btn coach-detail__btn--danger">
            Release
          </button>
        </div>
      </div>
    </div>
  );
};

interface CoachGroupProps {
  title: string;
  coaches: Coach[];
  isExpanded: boolean;
  onToggle: () => void;
  onCoachClick: (id: string) => void;
  onPopOut?: (coach: Coach) => void;
}

const CoachGroup: React.FC<CoachGroupProps> = ({
  title,
  coaches,
  isExpanded,
  onToggle,
  onCoachClick,
  onPopOut
}) => {
  if (coaches.length === 0) return null;

  return (
    <div className="coaches-group">
      <button className="coaches-group__header" onClick={onToggle}>
        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <span className="coaches-group__title">{title}</span>
        <span className="coaches-group__count">{coaches.length}</span>
      </button>

      {isExpanded && (
        <table className="coaches-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>RTG</th>
              <th>EXP</th>
              <th>Scheme/Spec</th>
              <th>CTR</th>
              <th>SAL</th>
              <th></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {coaches.map(coach => (
              <CoachRow
                key={coach.id}
                coach={coach}
                onClick={() => onCoachClick(coach.id)}
                onPopOut={() => onPopOut?.(coach)}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

// === Main Component ===

interface CoachesContentProps {
  onAddCoachToWorkspace?: (coach: { id: string; name: string; role: string; rating: number }) => void;
}

export const CoachesContent: React.FC<CoachesContentProps> = ({ onAddCoachToWorkspace }) => {
  const [view, setView] = useState<CoachView>({ type: 'list' });
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(['head', 'coordinators', 'offense', 'defense'])
  );

  const toggleGroup = (group: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(group)) {
        next.delete(group);
      } else {
        next.add(group);
      }
      return next;
    });
  };

  // Group coaches by category
  const headCoach = DEMO_COACHES.filter(c => c.role === 'HC');
  const coordinators = DEMO_COACHES.filter(c => ['OC', 'DC', 'STC'].includes(c.role));
  const offenseCoaches = DEMO_COACHES.filter(c => ['QB', 'RB', 'WR', 'TE', 'OL'].includes(c.role));
  const defenseCoaches = DEMO_COACHES.filter(c => ['DL', 'LB', 'DB'].includes(c.role));

  const handlePopOut = (coach: Coach) => {
    onAddCoachToWorkspace?.({
      id: coach.id,
      name: coach.name,
      role: ROLE_LABELS[coach.role],
      rating: coach.rating,
    });
  };

  if (view.type === 'coach') {
    const coach = DEMO_COACHES.find(c => c.id === view.coachId);
    if (coach) {
      return (
        <div className="ref-content">
          <CoachDetail coach={coach} onBack={() => setView({ type: 'list' })} />
        </div>
      );
    }
  }

  return (
    <div className="ref-content">
      <div className="coaches-content">
        {/* Summary Stats */}
        <div className="coaches-summary">
          <div className="coaches-summary__stat">
            <span className="coaches-summary__value">{DEMO_COACHES.length}</span>
            <span className="coaches-summary__label">Total Staff</span>
          </div>
          <div className="coaches-summary__stat">
            <span className="coaches-summary__value" style={{ color: 'var(--success)' }}>
              {DEMO_COACHES.filter(c => c.rating >= 80).length}
            </span>
            <span className="coaches-summary__label">Elite (80+)</span>
          </div>
          <div className="coaches-summary__stat">
            <span className="coaches-summary__value" style={{ color: 'var(--danger)' }}>
              {DEMO_COACHES.filter(c => c.contractYears === 1).length}
            </span>
            <span className="coaches-summary__label">Expiring</span>
          </div>
          <div className="coaches-summary__stat">
            <span className="coaches-summary__value">
              {formatSalary(DEMO_COACHES.reduce((sum, c) => sum + c.salary, 0))}
            </span>
            <span className="coaches-summary__label">Total Salary</span>
          </div>
        </div>

        {/* Coach Groups */}
        <div className="coaches-groups">
          <CoachGroup
            title="Head Coach"
            coaches={headCoach}
            isExpanded={expandedGroups.has('head')}
            onToggle={() => toggleGroup('head')}
            onCoachClick={(id) => setView({ type: 'coach', coachId: id })}
            onPopOut={handlePopOut}
          />

          <CoachGroup
            title="Coordinators"
            coaches={coordinators}
            isExpanded={expandedGroups.has('coordinators')}
            onToggle={() => toggleGroup('coordinators')}
            onCoachClick={(id) => setView({ type: 'coach', coachId: id })}
            onPopOut={handlePopOut}
          />

          <CoachGroup
            title="Offensive Coaches"
            coaches={offenseCoaches}
            isExpanded={expandedGroups.has('offense')}
            onToggle={() => toggleGroup('offense')}
            onCoachClick={(id) => setView({ type: 'coach', coachId: id })}
            onPopOut={handlePopOut}
          />

          <CoachGroup
            title="Defensive Coaches"
            coaches={defenseCoaches}
            isExpanded={expandedGroups.has('defense')}
            onToggle={() => toggleGroup('defense')}
            onCoachClick={(id) => setView({ type: 'coach', coachId: id })}
            onPopOut={handlePopOut}
          />
        </div>
      </div>
    </div>
  );
};

export default CoachesContent;
