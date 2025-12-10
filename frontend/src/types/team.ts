/**
 * Team and player types matching the backend Pydantic schemas
 */

export type Position =
  | 'QB'
  | 'RB'
  | 'WR'
  | 'TE'
  | 'LT'
  | 'LG'
  | 'C'
  | 'RG'
  | 'RT'
  | 'DE'
  | 'DT'
  | 'OLB'
  | 'MLB'
  | 'CB'
  | 'FS'
  | 'SS'
  | 'K'
  | 'P';

export interface Player {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  position: Position;
  number: number;
  overall: number;
  speed: number;
  strength: number;
  awareness: number;
  injury_status: string;
}

export interface Roster {
  quarterbacks: Player[];
  running_backs: Player[];
  wide_receivers: Player[];
  tight_ends: Player[];
  offensive_line: Player[];
  defensive_line: Player[];
  linebackers: Player[];
  defensive_backs: Player[];
  kickers: Player[];
  punters: Player[];
}

export interface TeamSummary {
  id: string;
  name: string;
  abbreviation: string;
  city: string;
  full_name: string;
  primary_color: string;
  secondary_color: string;
  offense_rating: number;
  defense_rating: number;
}

export interface Team extends TeamSummary {
  roster: Roster;
}

export interface StarterInfo {
  qb: Player | null;
  rb1: Player | null;
  wr1: Player | null;
  wr2: Player | null;
  te: Player | null;
  lt: Player | null;
  lg: Player | null;
  c: Player | null;
  rg: Player | null;
  rt: Player | null;
  de1: Player | null;
  de2: Player | null;
  dt: Player | null;
  olb1: Player | null;
  olb2: Player | null;
  mlb: Player | null;
  cb1: Player | null;
  cb2: Player | null;
  fs: Player | null;
  ss: Player | null;
  k: Player | null;
  p: Player | null;
}
