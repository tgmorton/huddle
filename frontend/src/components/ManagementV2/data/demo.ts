// Demo data for ManagementV2

import type { GameEvent, WorkspaceItem, NewsItem, Player, PlayerStats } from '../types';

// Helper to get demo event by ID
export const getDemoEvent = (eventId: string): GameEvent | undefined => {
  return DEMO_EVENTS.find(e => e.id === eventId);
};

export const DEMO_EVENTS: GameEvent[] = [
  {
    id: 'evt1',
    type: 'injury',
    title: 'Injury Report',
    subtitle: 'Marcus Johnson (QB)',
    description: 'Your starting quarterback suffered a shoulder strain during practice. Medical staff recommends rest.',
    severity: 'critical',
    options: [
      { label: 'Rest 1 Week', variant: 'primary' },
      { label: 'Play Through It', variant: 'danger' },
      { label: 'Get Second Opinion', variant: 'secondary' },
    ],
  },
  {
    id: 'evt2',
    type: 'trade_offer',
    title: 'Trade Offer Received',
    subtitle: 'From: Dallas Cowboys',
    description: 'Dallas is offering their 2nd round pick and a backup RB for your WR Tyler Brown. They need receiver depth.',
    severity: 'info',
    options: [
      { label: 'Accept Trade', variant: 'primary' },
      { label: 'Counter Offer', variant: 'secondary' },
      { label: 'Decline', variant: 'danger' },
    ],
  },
  {
    id: 'evt3',
    type: 'media',
    title: 'Press Conference',
    subtitle: 'Media Question',
    description: '"Coach, there are rumors about tension in the locker room after last week\'s loss. Can you address the team chemistry situation?"',
    severity: 'warning',
    options: [
      { label: 'Deflect', variant: 'secondary' },
      { label: 'Address Directly', variant: 'primary' },
      { label: 'No Comment', variant: 'secondary' },
    ],
  },
  {
    id: 'evt4',
    type: 'contract_demand',
    title: 'Contract Demands',
    subtitle: 'Jaylen Smith (WR)',
    description: 'Your star receiver wants to renegotiate his contract. He\'s seeking $26M/year, up from his current $22M. He hints he may hold out if not addressed.',
    severity: 'warning',
    options: [
      { label: 'Open Negotiations', variant: 'primary' },
      { label: 'Refuse to Negotiate', variant: 'danger' },
      { label: 'Promise After Season', variant: 'secondary' },
    ],
  },
];

// Convert demo events to workspace items
export const INITIAL_WORKSPACE_ITEMS: WorkspaceItem[] = DEMO_EVENTS.map(event => ({
  id: `demo-${event.id}`,
  type: event.type === 'contract_demand' ? 'decision' as const :
        event.type === 'trade_offer' ? 'decision' as const :
        event.type === 'injury' ? 'deadline' as const :
        'meeting' as const,
  title: event.title,
  subtitle: event.subtitle,
  detail: event.description,
  timeLeft: event.severity === 'critical' ? 'Today' : event.severity === 'warning' ? '1d' : undefined,
  isOpen: false,
  status: 'active' as const,
  // Store original event type for pane rendering
  eventId: event.id,
}));

export const DEMO_NEWS: NewsItem[] = [
  { id: '1', text: 'Cowboys lose starting QB to injury, out 4-6 weeks', isBreaking: true },
  { id: '2', text: 'League announces new overtime rules for playoffs' },
  { id: '3', text: 'Giants sign veteran CB from practice squad' },
];

export const DEMO_PLAYERS: Player[] = [
  { id: 'qb1', name: 'M. Johnson', position: 'QB', number: 12, age: 27, experience: '5th year', overall: 88, salary: '$28.5M', contractYears: 3, morale: 'high', traits: ['Leader', 'Clutch', 'Film Junkie'] },
  { id: 'qb2', name: 'R. Garcia', position: 'QB', number: 8, age: 25, experience: '2nd year', overall: 72, salary: '$1.1M', contractYears: 2, morale: 'neutral', traits: ['Gunslinger', 'Scrambler'] },
  { id: 'rb1', name: 'D. Williams', position: 'RB', number: 22, age: 24, experience: '3rd year', overall: 85, salary: '$4.2M', contractYears: 2, morale: 'high', traits: ['Workhorse', 'Team Player'] },
  { id: 'rb2', name: 'T. Murray', position: 'RB', number: 34, age: 23, experience: '2nd year', overall: 74, salary: '$0.9M', contractYears: 3, morale: 'high', traits: ['Speed Back', 'Return Man'] },
  { id: 'wr1', name: 'J. Smith', position: 'WR', number: 81, age: 26, experience: '4th year', overall: 91, salary: '$22.0M', contractYears: 4, morale: 'neutral', traits: ['Diva', 'Playmaker', 'Route Technician'] },
  { id: 'wr2', name: 'T. Brown', position: 'WR', number: 15, age: 23, experience: '2nd year', overall: 82, salary: '$1.8M', contractYears: 3, morale: 'high', traits: ['Deep Threat', 'Eager Learner'] },
  { id: 'wr3', name: 'K. Davis', position: 'WR', number: 88, age: 29, experience: '7th year', overall: 79, salary: '$8.5M', contractYears: 1, morale: 'low', traits: ['Veteran Presence', 'Slot Specialist'] },
  { id: 'wr4', name: 'A. Cooper', position: 'WR', number: 17, age: 24, experience: '2nd year', overall: 74, salary: '$0.9M', contractYears: 2, morale: 'high', traits: ['Special Teams'] },
  { id: 'te1', name: 'C. Wilson', position: 'TE', number: 85, age: 27, experience: '5th year', overall: 80, salary: '$6.5M', contractYears: 2, morale: 'high', traits: ['Blocker', 'Red Zone Threat'] },
  { id: 'de1', name: 'R. Miller', position: 'DE', number: 97, age: 28, experience: '6th year', overall: 89, salary: '$18.0M', contractYears: 2, morale: 'high', traits: ['Motor', 'Pass Rush Specialist'] },
  { id: 'dt1', name: 'A. Donald', position: 'DT', number: 99, age: 30, experience: '8th year', overall: 86, salary: '$20.0M', contractYears: 1, morale: 'neutral', traits: ['Disruptor', 'Veteran'] },
  { id: 'lb1', name: 'A. Jackson', position: 'LB', number: 54, age: 27, experience: '5th year', overall: 87, salary: '$14.0M', contractYears: 3, morale: 'high', traits: ['Leader', 'Tackling Machine', 'Film Junkie'] },
  { id: 'cb1', name: 'J. Ramsey', position: 'CB', number: 21, age: 27, experience: '6th year', overall: 88, salary: '$16.5M', contractYears: 3, morale: 'high', traits: ['Lockdown', 'Trash Talker'] },
  { id: 'cb2', name: 'D. Ward', position: 'CB', number: 24, age: 25, experience: '4th year', overall: 82, salary: '$8.2M', contractYears: 2, morale: 'high', traits: ['Ball Hawk'] },
  { id: 'fs1', name: 'M. Hooker', position: 'S', number: 29, age: 26, experience: '5th year', overall: 80, salary: '$7.0M', contractYears: 2, morale: 'neutral', traits: ['Range', 'Playmaker'] },
  { id: 'ss1', name: 'J. Bates', position: 'S', number: 30, age: 25, experience: '4th year', overall: 84, salary: '$10.0M', contractYears: 3, morale: 'high', traits: ['Hard Hitter', 'Leader'] },
];

// Demo roster for depth chart with position-specific attributes
export const DEMO_ROSTER: PlayerStats[] = [
  // Quarterbacks
  { id: 'qb1', name: 'M. Johnson', pos: 'QB', ovr: 88, depth: 1, attrs: { ARM: 92, ACC: 86, AWR: 88, SPD: 78 } },
  { id: 'qb2', name: 'R. Garcia', pos: 'QB', ovr: 72, depth: 2, attrs: { ARM: 74, ACC: 70, AWR: 68, SPD: 72 } },
  // Running backs
  { id: 'rb1', name: 'D. Williams', pos: 'RB', ovr: 85, depth: 1, attrs: { SPD: 91, AGI: 88, BTK: 82, CAR: 84 } },
  { id: 'rb2', name: 'T. Murray', pos: 'RB', ovr: 74, depth: 2, attrs: { SPD: 86, AGI: 78, BTK: 70, CAR: 72 } },
  // Wide receivers (WR1, WR2, WR3 starters, then backups)
  { id: 'wr1', name: 'J. Smith', pos: 'WR', ovr: 91, depth: 1, attrs: { SPD: 94, CTH: 92, RTE: 90, REL: 88 } },
  { id: 'wr2', name: 'T. Brown', pos: 'WR', ovr: 82, depth: 2, attrs: { SPD: 88, CTH: 84, RTE: 78, REL: 80 } },
  { id: 'wr3', name: 'K. Davis', pos: 'WR', ovr: 79, depth: 3, attrs: { SPD: 90, CTH: 76, RTE: 74, REL: 82 } },
  { id: 'wr4', name: 'A. Cooper', pos: 'WR', ovr: 74, depth: 4, attrs: { SPD: 85, CTH: 72, RTE: 70, REL: 74 } },
  { id: 'wr5', name: 'M. Hall', pos: 'WR', ovr: 68, depth: 5, attrs: { SPD: 82, CTH: 66, RTE: 62, REL: 68 } },
  // Tight ends
  { id: 'te1', name: 'C. Wilson', pos: 'TE', ovr: 80, depth: 1, attrs: { CTH: 82, RBK: 74, SPD: 78, STR: 76 } },
  { id: 'te2', name: 'J. Peters', pos: 'TE', ovr: 71, depth: 2, attrs: { CTH: 70, RBK: 72, SPD: 68, STR: 74 } },
  // Offensive line
  { id: 'lt1', name: 'T. Adams', pos: 'LT', ovr: 84, depth: 1, attrs: { STR: 86, PBK: 88, RBK: 78, AWR: 82 } },
  { id: 'lg1', name: 'M. Nelson', pos: 'LG', ovr: 82, depth: 1, attrs: { STR: 88, PBK: 84, RBK: 80, AWR: 76 } },
  { id: 'c1', name: 'J. Kelly', pos: 'C', ovr: 81, depth: 1, attrs: { STR: 82, PBK: 84, RBK: 78, AWR: 86 } },
  { id: 'rg1', name: 'W. Martin', pos: 'RG', ovr: 79, depth: 1, attrs: { STR: 84, PBK: 80, RBK: 82, AWR: 72 } },
  { id: 'rt1', name: 'L. Collins', pos: 'RT', ovr: 83, depth: 1, attrs: { STR: 85, PBK: 86, RBK: 76, AWR: 78 } },
  { id: 'ol2', name: 'R. Scott', pos: 'LT', ovr: 69, depth: 2, attrs: { STR: 72, PBK: 68, RBK: 66, AWR: 64 } },
  { id: 'ol3', name: 'D. Brown', pos: 'C', ovr: 70, depth: 2, attrs: { STR: 74, PBK: 70, RBK: 68, AWR: 72 } },
  // Defensive line
  { id: 'de1', name: 'R. Miller', pos: 'DE', ovr: 89, depth: 1, attrs: { STR: 88, PWM: 92, BSH: 86, SPD: 84 } },
  { id: 'dt1', name: 'A. Donald', pos: 'DT', ovr: 86, depth: 1, attrs: { STR: 92, PWM: 88, BSH: 90, SPD: 72 } },
  { id: 'de2', name: 'C. Thompson', pos: 'DE', ovr: 83, depth: 2, attrs: { STR: 82, PWM: 84, BSH: 80, SPD: 82 } },
  { id: 'dt2', name: 'J. Allen', pos: 'DT', ovr: 75, depth: 2, attrs: { STR: 80, PWM: 74, BSH: 72, SPD: 66 } },
  // Linebackers
  { id: 'lb1', name: 'A. Jackson', pos: 'LB', ovr: 87, depth: 1, attrs: { TAK: 90, SPD: 86, AWR: 88, COV: 78 } },
  { id: 'lb2', name: 'M. White', pos: 'LB', ovr: 76, depth: 2, attrs: { TAK: 78, SPD: 80, AWR: 72, COV: 68 } },
  // Cornerbacks
  { id: 'cb1', name: 'J. Ramsey', pos: 'CB', ovr: 88, depth: 1, attrs: { SPD: 92, MCV: 90, ZCV: 86, PRS: 82 } },
  { id: 'cb2', name: 'D. Ward', pos: 'CB', ovr: 82, depth: 1, attrs: { SPD: 90, MCV: 84, ZCV: 80, PRS: 76 } },
  { id: 'cb3', name: 'T. Hill', pos: 'CB', ovr: 73, depth: 2, attrs: { SPD: 88, MCV: 72, ZCV: 70, PRS: 68 } },
  // Safeties
  { id: 'fs1', name: 'M. Hooker', pos: 'FS', ovr: 80, depth: 1, attrs: { SPD: 88, ZCV: 84, TAK: 72, AWR: 82 } },
  { id: 'ss1', name: 'J. Bates', pos: 'SS', ovr: 84, depth: 1, attrs: { SPD: 86, ZCV: 82, TAK: 84, AWR: 80 } },
  { id: 's2', name: 'C. Davis', pos: 'FS', ovr: 71, depth: 2, attrs: { SPD: 84, ZCV: 70, TAK: 68, AWR: 66 } },
  { id: 's3', name: 'R. Neal', pos: 'SS', ovr: 69, depth: 2, attrs: { SPD: 82, ZCV: 66, TAK: 70, AWR: 64 } },
];
