/**
 * Mock Stats Generator
 *
 * Generates realistic placeholder statistics based on player attributes.
 * Used for development until backend API is ready.
 */

import type {
  PlayerSeasonRow,
  PlayerCareerStats,
  CareerHighs,
  PassingSeasonStats,
  RushingSeasonStats,
  ReceivingSeasonStats,
  BlockingSeasonStats,
  DefensiveSeasonStats,
  KickingSeasonStats,
  PuntingSeasonStats,
  LeagueLeader,
  LeagueLeadersCategory,
  StatCategory,
  POSITION_TO_STAT_GROUP,
} from '../types/stats';

// === Helpers ===

function randomInRange(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function randomInt(min: number, max: number): number {
  return Math.floor(randomInRange(min, max + 1));
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

// Calculate NFL passer rating
function calculatePasserRating(
  completions: number,
  attempts: number,
  yards: number,
  touchdowns: number,
  interceptions: number
): number {
  if (attempts === 0) return 0;

  const a = clamp(((completions / attempts) - 0.3) * 5, 0, 2.375);
  const b = clamp(((yards / attempts) - 3) * 0.25, 0, 2.375);
  const c = clamp((touchdowns / attempts) * 20, 0, 2.375);
  const d = clamp(2.375 - ((interceptions / attempts) * 25), 0, 2.375);

  return ((a + b + c + d) / 6) * 100;
}

// === Stat Ranges by Position ===

interface StatRange {
  min: number;
  max: number;
}

const QB_RANGES = {
  attempts: { min: 300, max: 650 },
  completion_pct: { min: 58, max: 72 },
  yards: { min: 2500, max: 5500 },
  touchdowns: { min: 12, max: 50 },
  interceptions: { min: 4, max: 20 },
  sacks: { min: 15, max: 55 },
  longest: { min: 40, max: 85 },
};

const RB_RANGES = {
  attempts: { min: 100, max: 350 },
  yards: { min: 400, max: 2000 },
  touchdowns: { min: 2, max: 18 },
  fumbles: { min: 0, max: 5 },
  longest: { min: 25, max: 80 },
  first_downs: { min: 20, max: 100 },
};

const WR_RANGES = {
  targets: { min: 50, max: 180 },
  receptions: { min: 30, max: 130 },
  yards: { min: 300, max: 1800 },
  touchdowns: { min: 1, max: 14 },
  drops: { min: 1, max: 8 },
  longest: { min: 30, max: 85 },
  first_downs: { min: 15, max: 80 },
};

const TE_RANGES = {
  targets: { min: 30, max: 140 },
  receptions: { min: 20, max: 100 },
  yards: { min: 200, max: 1200 },
  touchdowns: { min: 1, max: 12 },
  drops: { min: 1, max: 5 },
  longest: { min: 20, max: 70 },
  first_downs: { min: 10, max: 50 },
};

const DEF_RANGES = {
  tackles: { min: 20, max: 150 },
  tackles_for_loss: { min: 0, max: 25 },
  sacks: { min: 0, max: 20 },
  qb_hits: { min: 0, max: 35 },
  interceptions: { min: 0, max: 8 },
  passes_defended: { min: 0, max: 20 },
  forced_fumbles: { min: 0, max: 5 },
};

// === Season Stats Generators ===

function generatePassingStats(
  overall: number,
  gamesPlayed: number,
  experience: number
): PassingSeasonStats {
  const qualityFactor = overall / 100;
  const volumeFactor = (gamesPlayed / 17) * Math.min(1, 0.5 + experience * 0.1);

  const attempts = Math.round(
    randomInRange(QB_RANGES.attempts.min, QB_RANGES.attempts.max) * volumeFactor
  );
  const compPct = randomInRange(
    QB_RANGES.completion_pct.min,
    QB_RANGES.completion_pct.max
  ) * (0.85 + qualityFactor * 0.15);
  const completions = Math.round(attempts * (compPct / 100));
  const yards = Math.round(
    randomInRange(QB_RANGES.yards.min, QB_RANGES.yards.max) * volumeFactor * qualityFactor
  );
  const touchdowns = Math.round(
    randomInRange(QB_RANGES.touchdowns.min, QB_RANGES.touchdowns.max) * volumeFactor * qualityFactor
  );
  const interceptions = Math.round(
    randomInRange(QB_RANGES.interceptions.min, QB_RANGES.interceptions.max) *
      volumeFactor *
      (2 - qualityFactor)
  );
  const sacks = Math.round(
    randomInRange(QB_RANGES.sacks.min, QB_RANGES.sacks.max) * volumeFactor * (1.5 - qualityFactor * 0.5)
  );

  return {
    attempts,
    completions,
    yards,
    touchdowns,
    interceptions,
    sacks,
    sack_yards_lost: Math.round(sacks * randomInRange(5, 8)),
    longest: randomInt(QB_RANGES.longest.min, QB_RANGES.longest.max),
    completion_pct: Math.round(compPct * 10) / 10,
    yards_per_attempt: Math.round((yards / attempts) * 100) / 100,
    passer_rating: Math.round(
      calculatePasserRating(completions, attempts, yards, touchdowns, interceptions) * 10
    ) / 10,
  };
}

function generateRushingStats(
  overall: number,
  gamesPlayed: number,
  experience: number,
  isRB: boolean
): RushingSeasonStats {
  const qualityFactor = overall / 100;
  const volumeFactor = (gamesPlayed / 17) * Math.min(1, 0.6 + experience * 0.1);
  const positionFactor = isRB ? 1 : 0.15; // QBs/WRs get fewer carries

  const attempts = Math.round(
    randomInRange(RB_RANGES.attempts.min, RB_RANGES.attempts.max) * volumeFactor * positionFactor
  );
  const ypc = randomInRange(3.2, 5.5) * (0.8 + qualityFactor * 0.4);
  const yards = Math.round(attempts * ypc);
  const touchdowns = Math.round(
    randomInRange(RB_RANGES.touchdowns.min, RB_RANGES.touchdowns.max) *
      volumeFactor *
      qualityFactor *
      positionFactor
  );

  return {
    attempts,
    yards,
    touchdowns,
    fumbles: randomInt(0, Math.ceil(3 * (2 - qualityFactor))),
    fumbles_lost: randomInt(0, 2),
    longest: randomInt(RB_RANGES.longest.min, RB_RANGES.longest.max),
    first_downs: Math.round(attempts * randomInRange(0.15, 0.3)),
    yards_per_carry: Math.round(ypc * 10) / 10,
  };
}

function generateReceivingStats(
  overall: number,
  gamesPlayed: number,
  experience: number,
  isTE: boolean
): ReceivingSeasonStats {
  const qualityFactor = overall / 100;
  const volumeFactor = (gamesPlayed / 17) * Math.min(1, 0.6 + experience * 0.1);
  const ranges = isTE ? TE_RANGES : WR_RANGES;

  const targets = Math.round(
    randomInRange(ranges.targets.min, ranges.targets.max) * volumeFactor * qualityFactor
  );
  const catchRate = randomInRange(58, 78) * (0.9 + qualityFactor * 0.2);
  const receptions = Math.round(targets * (catchRate / 100));
  const ypr = randomInRange(isTE ? 9 : 11, isTE ? 14 : 18);
  const yards = Math.round(receptions * ypr);

  return {
    targets,
    receptions,
    yards,
    touchdowns: Math.round(
      randomInRange(ranges.touchdowns.min, ranges.touchdowns.max) * volumeFactor * qualityFactor
    ),
    drops: randomInt(ranges.drops.min, ranges.drops.max),
    longest: randomInt(ranges.longest.min, ranges.longest.max),
    first_downs: Math.round(receptions * randomInRange(0.35, 0.55)),
    yards_per_reception: Math.round(ypr * 10) / 10,
    catch_rate: Math.round(catchRate * 10) / 10,
  };
}

function generateBlockingStats(
  overall: number,
  gamesPlayed: number
): BlockingSeasonStats {
  const qualityFactor = overall / 100;
  const snaps = Math.round(gamesPlayed * randomInRange(55, 75));

  return {
    snaps,
    sacks_allowed: Math.round(randomInRange(0, 8) * (2 - qualityFactor)),
    pressures_allowed: Math.round(randomInRange(10, 40) * (2 - qualityFactor)),
    penalties: randomInt(1, Math.ceil(8 * (2 - qualityFactor))),
    pancakes: Math.round(randomInRange(5, 30) * qualityFactor),
    pass_block_grade: Math.round(50 + qualityFactor * 40 + randomInRange(-10, 10)),
    run_block_grade: Math.round(50 + qualityFactor * 40 + randomInRange(-10, 10)),
  };
}

function generateDefensiveStats(
  overall: number,
  gamesPlayed: number,
  positionGroup: string
): DefensiveSeasonStats {
  const qualityFactor = overall / 100;
  const volumeFactor = gamesPlayed / 17;

  // Position-specific adjustments
  const isDL = positionGroup === 'DL';
  const isLB = positionGroup === 'LB';
  const isDB = positionGroup === 'DB';

  const tackleBase = isDL ? 40 : isLB ? 100 : 60;
  const sackBase = isDL ? 8 : isLB ? 3 : 1;
  const intBase = isDL ? 0 : isLB ? 2 : 4;
  const pdBase = isDL ? 2 : isLB ? 6 : 12;

  const tackles = Math.round(
    randomInRange(tackleBase * 0.5, tackleBase * 1.5) * volumeFactor * qualityFactor
  );

  return {
    tackles,
    tackles_solo: Math.round(tackles * randomInRange(0.55, 0.75)),
    tackles_assisted: Math.round(tackles * randomInRange(0.25, 0.45)),
    tackles_for_loss: Math.round(randomInRange(2, 20) * volumeFactor * qualityFactor * (isDL || isLB ? 1 : 0.3)),
    sacks: Math.round(randomInRange(0, sackBase * 2) * volumeFactor * qualityFactor * 10) / 10,
    qb_hits: Math.round(randomInRange(2, 25) * volumeFactor * qualityFactor * (isDL ? 1 : 0.5)),
    interceptions: Math.round(randomInRange(0, intBase * 2) * volumeFactor * qualityFactor),
    interception_yards: randomInt(0, 100),
    interception_tds: randomInt(0, 2),
    passes_defended: Math.round(randomInRange(pdBase * 0.3, pdBase * 1.5) * volumeFactor * qualityFactor),
    forced_fumbles: randomInt(0, Math.ceil(4 * qualityFactor)),
    fumble_recoveries: randomInt(0, 2),
    safeties: Math.random() < 0.05 ? 1 : 0,
  };
}

function generateKickingStats(
  overall: number,
  gamesPlayed: number
): KickingSeasonStats {
  const qualityFactor = overall / 100;
  const volumeFactor = gamesPlayed / 17;

  const fgAttempts = Math.round(randomInRange(20, 40) * volumeFactor);
  const fgPct = 70 + qualityFactor * 25 + randomInRange(-5, 5);
  const fgMade = Math.round(fgAttempts * (fgPct / 100));

  const xpAttempts = Math.round(randomInRange(25, 55) * volumeFactor);
  const xpPct = 90 + qualityFactor * 8 + randomInRange(-3, 2);
  const xpMade = Math.round(xpAttempts * (xpPct / 100));

  return {
    fg_attempts: fgAttempts,
    fg_made: fgMade,
    fg_long: randomInt(45, 60),
    fg_pct: Math.round(fgPct * 10) / 10,
    xp_attempts: xpAttempts,
    xp_made: xpMade,
    xp_pct: Math.round(xpPct * 10) / 10,
    points: fgMade * 3 + xpMade,
  };
}

function generatePuntingStats(
  overall: number,
  gamesPlayed: number
): PuntingSeasonStats {
  const qualityFactor = overall / 100;
  const volumeFactor = gamesPlayed / 17;

  const punts = Math.round(randomInRange(50, 90) * volumeFactor);
  const avgYards = 42 + qualityFactor * 8 + randomInRange(-2, 2);

  return {
    punts,
    punt_yards: Math.round(punts * avgYards),
    punt_avg: Math.round(avgYards * 10) / 10,
    punt_long: randomInt(55, 70),
    punts_inside_20: Math.round(punts * randomInRange(0.3, 0.5) * qualityFactor),
    touchbacks: Math.round(punts * randomInRange(0.05, 0.15) * (2 - qualityFactor)),
  };
}

// === Main Generator Functions ===

export function generateMockSeasonStats(
  position: string,
  overall: number,
  experience: number,
  gamesPlayed: number = 16,
  season: number = 2024,
  teamAbbr: string = 'TBD'
): PlayerSeasonRow {
  const posGroup = (POSITION_TO_STAT_GROUP as Record<string, string>)[position] || position;

  const base: PlayerSeasonRow = {
    season,
    team_abbr: teamAbbr,
    games_played: gamesPlayed,
    games_started: Math.min(gamesPlayed, gamesPlayed - randomInt(0, 2)),
  };

  // Add position-specific stats
  switch (posGroup) {
    case 'QB':
      base.passing = generatePassingStats(overall, gamesPlayed, experience);
      base.rushing = generateRushingStats(overall, gamesPlayed, experience, false);
      break;
    case 'RB':
      base.rushing = generateRushingStats(overall, gamesPlayed, experience, true);
      base.receiving = generateReceivingStats(overall, gamesPlayed, experience, false);
      break;
    case 'WR':
      base.receiving = generateReceivingStats(overall, gamesPlayed, experience, false);
      base.rushing = generateRushingStats(overall, gamesPlayed, experience, false);
      break;
    case 'TE':
      base.receiving = generateReceivingStats(overall, gamesPlayed, experience, true);
      base.blocking = generateBlockingStats(overall, gamesPlayed);
      break;
    case 'OL':
      base.blocking = generateBlockingStats(overall, gamesPlayed);
      break;
    case 'DL':
    case 'LB':
    case 'DB':
      base.defense = generateDefensiveStats(overall, gamesPlayed, posGroup);
      break;
    case 'K':
      base.kicking = generateKickingStats(overall, gamesPlayed);
      break;
    case 'P':
      base.punting = generatePuntingStats(overall, gamesPlayed);
      break;
  }

  return base;
}

function aggregateSeasons(seasons: PlayerSeasonRow[]): PlayerSeasonRow {
  if (seasons.length === 0) {
    return {
      season: 0,
      team_abbr: '---',
      games_played: 0,
      games_started: 0,
    };
  }

  const totals: PlayerSeasonRow = {
    season: 0, // Career
    team_abbr: '---',
    games_played: seasons.reduce((sum, s) => sum + s.games_played, 0),
    games_started: seasons.reduce((sum, s) => sum + s.games_started, 0),
  };

  // Aggregate passing
  if (seasons.some((s) => s.passing)) {
    const passSeasons = seasons.filter((s) => s.passing).map((s) => s.passing!);
    const attempts = passSeasons.reduce((sum, p) => sum + p.attempts, 0);
    const completions = passSeasons.reduce((sum, p) => sum + p.completions, 0);
    const yards = passSeasons.reduce((sum, p) => sum + p.yards, 0);
    const touchdowns = passSeasons.reduce((sum, p) => sum + p.touchdowns, 0);
    const interceptions = passSeasons.reduce((sum, p) => sum + p.interceptions, 0);

    totals.passing = {
      attempts,
      completions,
      yards,
      touchdowns,
      interceptions,
      sacks: passSeasons.reduce((sum, p) => sum + p.sacks, 0),
      sack_yards_lost: passSeasons.reduce((sum, p) => sum + p.sack_yards_lost, 0),
      longest: Math.max(...passSeasons.map((p) => p.longest)),
      completion_pct: attempts > 0 ? Math.round((completions / attempts) * 1000) / 10 : 0,
      yards_per_attempt: attempts > 0 ? Math.round((yards / attempts) * 100) / 100 : 0,
      passer_rating: Math.round(
        calculatePasserRating(completions, attempts, yards, touchdowns, interceptions) * 10
      ) / 10,
    };
  }

  // Aggregate rushing
  if (seasons.some((s) => s.rushing)) {
    const rushSeasons = seasons.filter((s) => s.rushing).map((s) => s.rushing!);
    const attempts = rushSeasons.reduce((sum, r) => sum + r.attempts, 0);
    const yards = rushSeasons.reduce((sum, r) => sum + r.yards, 0);

    totals.rushing = {
      attempts,
      yards,
      touchdowns: rushSeasons.reduce((sum, r) => sum + r.touchdowns, 0),
      fumbles: rushSeasons.reduce((sum, r) => sum + r.fumbles, 0),
      fumbles_lost: rushSeasons.reduce((sum, r) => sum + r.fumbles_lost, 0),
      longest: Math.max(...rushSeasons.map((r) => r.longest)),
      first_downs: rushSeasons.reduce((sum, r) => sum + r.first_downs, 0),
      yards_per_carry: attempts > 0 ? Math.round((yards / attempts) * 10) / 10 : 0,
    };
  }

  // Aggregate receiving
  if (seasons.some((s) => s.receiving)) {
    const recSeasons = seasons.filter((s) => s.receiving).map((s) => s.receiving!);
    const targets = recSeasons.reduce((sum, r) => sum + r.targets, 0);
    const receptions = recSeasons.reduce((sum, r) => sum + r.receptions, 0);
    const yards = recSeasons.reduce((sum, r) => sum + r.yards, 0);

    totals.receiving = {
      targets,
      receptions,
      yards,
      touchdowns: recSeasons.reduce((sum, r) => sum + r.touchdowns, 0),
      drops: recSeasons.reduce((sum, r) => sum + r.drops, 0),
      longest: Math.max(...recSeasons.map((r) => r.longest)),
      first_downs: recSeasons.reduce((sum, r) => sum + r.first_downs, 0),
      yards_per_reception: receptions > 0 ? Math.round((yards / receptions) * 10) / 10 : 0,
      catch_rate: targets > 0 ? Math.round((receptions / targets) * 1000) / 10 : 0,
    };
  }

  // Aggregate defense
  if (seasons.some((s) => s.defense)) {
    const defSeasons = seasons.filter((s) => s.defense).map((s) => s.defense!);

    totals.defense = {
      tackles: defSeasons.reduce((sum, d) => sum + d.tackles, 0),
      tackles_solo: defSeasons.reduce((sum, d) => sum + d.tackles_solo, 0),
      tackles_assisted: defSeasons.reduce((sum, d) => sum + d.tackles_assisted, 0),
      tackles_for_loss: defSeasons.reduce((sum, d) => sum + d.tackles_for_loss, 0),
      sacks: Math.round(defSeasons.reduce((sum, d) => sum + d.sacks, 0) * 10) / 10,
      qb_hits: defSeasons.reduce((sum, d) => sum + d.qb_hits, 0),
      interceptions: defSeasons.reduce((sum, d) => sum + d.interceptions, 0),
      interception_yards: defSeasons.reduce((sum, d) => sum + d.interception_yards, 0),
      interception_tds: defSeasons.reduce((sum, d) => sum + d.interception_tds, 0),
      passes_defended: defSeasons.reduce((sum, d) => sum + d.passes_defended, 0),
      forced_fumbles: defSeasons.reduce((sum, d) => sum + d.forced_fumbles, 0),
      fumble_recoveries: defSeasons.reduce((sum, d) => sum + d.fumble_recoveries, 0),
      safeties: defSeasons.reduce((sum, d) => sum + d.safeties, 0),
    };
  }

  // Aggregate kicking
  if (seasons.some((s) => s.kicking)) {
    const kickSeasons = seasons.filter((s) => s.kicking).map((s) => s.kicking!);
    const fgAttempts = kickSeasons.reduce((sum, k) => sum + k.fg_attempts, 0);
    const fgMade = kickSeasons.reduce((sum, k) => sum + k.fg_made, 0);
    const xpAttempts = kickSeasons.reduce((sum, k) => sum + k.xp_attempts, 0);
    const xpMade = kickSeasons.reduce((sum, k) => sum + k.xp_made, 0);

    totals.kicking = {
      fg_attempts: fgAttempts,
      fg_made: fgMade,
      fg_long: Math.max(...kickSeasons.map((k) => k.fg_long)),
      fg_pct: fgAttempts > 0 ? Math.round((fgMade / fgAttempts) * 1000) / 10 : 0,
      xp_attempts: xpAttempts,
      xp_made: xpMade,
      xp_pct: xpAttempts > 0 ? Math.round((xpMade / xpAttempts) * 1000) / 10 : 0,
      points: fgMade * 3 + xpMade,
    };
  }

  // Aggregate punting
  if (seasons.some((s) => s.punting)) {
    const puntSeasons = seasons.filter((s) => s.punting).map((s) => s.punting!);
    const punts = puntSeasons.reduce((sum, p) => sum + p.punts, 0);
    const yards = puntSeasons.reduce((sum, p) => sum + p.punt_yards, 0);

    totals.punting = {
      punts,
      punt_yards: yards,
      punt_avg: punts > 0 ? Math.round((yards / punts) * 10) / 10 : 0,
      punt_long: Math.max(...puntSeasons.map((p) => p.punt_long)),
      punts_inside_20: puntSeasons.reduce((sum, p) => sum + p.punts_inside_20, 0),
      touchbacks: puntSeasons.reduce((sum, p) => sum + p.touchbacks, 0),
    };
  }

  return totals;
}

function extractCareerHighs(seasons: PlayerSeasonRow[]): CareerHighs {
  const highs: CareerHighs = {};

  const passSeasons = seasons.filter((s) => s.passing);
  if (passSeasons.length > 0) {
    highs.passing_yards_season = Math.max(...passSeasons.map((s) => s.passing!.yards));
    highs.passing_tds_season = Math.max(...passSeasons.map((s) => s.passing!.touchdowns));
    highs.passer_rating_season = Math.max(...passSeasons.map((s) => s.passing!.passer_rating));
    // Estimate game highs
    highs.passing_yards_game = Math.round(highs.passing_yards_season * randomInRange(0.08, 0.12));
    highs.passing_tds_game = Math.min(6, Math.ceil(highs.passing_tds_season * 0.15));
  }

  const rushSeasons = seasons.filter((s) => s.rushing);
  if (rushSeasons.length > 0) {
    highs.rushing_yards_season = Math.max(...rushSeasons.map((s) => s.rushing!.yards));
    highs.rushing_tds_season = Math.max(...rushSeasons.map((s) => s.rushing!.touchdowns));
    highs.rushing_yards_game = Math.round(highs.rushing_yards_season * randomInRange(0.1, 0.15));
    highs.rushing_tds_game = Math.min(4, Math.ceil(highs.rushing_tds_season * 0.2));
  }

  const recSeasons = seasons.filter((s) => s.receiving);
  if (recSeasons.length > 0) {
    highs.receiving_yards_season = Math.max(...recSeasons.map((s) => s.receiving!.yards));
    highs.receptions_season = Math.max(...recSeasons.map((s) => s.receiving!.receptions));
    highs.receiving_tds_season = Math.max(...recSeasons.map((s) => s.receiving!.touchdowns));
    highs.receiving_yards_game = Math.round(highs.receiving_yards_season * randomInRange(0.1, 0.15));
    highs.receptions_game = Math.round(highs.receptions_season * randomInRange(0.08, 0.12));
    highs.receiving_tds_game = Math.min(3, Math.ceil(highs.receiving_tds_season * 0.25));
  }

  const defSeasons = seasons.filter((s) => s.defense);
  if (defSeasons.length > 0) {
    highs.sacks_season = Math.max(...defSeasons.map((s) => s.defense!.sacks));
    highs.interceptions_season = Math.max(...defSeasons.map((s) => s.defense!.interceptions));
    highs.tackles_game = Math.round(
      Math.max(...defSeasons.map((s) => s.defense!.tackles)) * randomInRange(0.1, 0.15)
    );
    highs.sacks_game = Math.min(4, Math.ceil(highs.sacks_season * 0.2));
  }

  return highs;
}

export function generateMockCareerStats(
  playerId: string,
  playerName: string,
  position: string,
  overall: number,
  experience: number
): PlayerCareerStats {
  const seasons: PlayerSeasonRow[] = [];
  const currentYear = 2024;

  // Generate past seasons
  for (let i = 0; i < experience; i++) {
    const seasonYear = currentYear - experience + i + 1;
    // Overall was lower in past years (growth trajectory)
    const pastOverall = Math.max(60, overall - (experience - i - 1) * randomInRange(1, 3));
    // First year often has fewer games
    const gamesPlayed = i === 0 ? randomInt(4, 16) : randomInt(12, 17);

    seasons.push(
      generateMockSeasonStats(position, pastOverall, i + 1, gamesPlayed, seasonYear, 'TBD')
    );
  }

  return {
    player_id: playerId,
    player_name: playerName,
    position,
    seasons,
    career_totals: aggregateSeasons(seasons),
    career_highs: extractCareerHighs(seasons),
  };
}

// === League Leaders Generator ===

const MOCK_TEAM_ABBRS = [
  'BUF', 'MIA', 'NE', 'NYJ', 'BAL', 'CIN', 'CLE', 'PIT',
  'HOU', 'IND', 'JAX', 'TEN', 'DEN', 'KC', 'LV', 'LAC',
  'DAL', 'NYG', 'PHI', 'WAS', 'CHI', 'DET', 'GB', 'MIN',
  'ATL', 'CAR', 'NO', 'TB', 'ARI', 'LAR', 'SF', 'SEA',
];

const MOCK_FIRST_NAMES = [
  'Patrick', 'Josh', 'Lamar', 'Justin', 'Joe', 'Tua', 'Trevor', 'Jalen',
  'Derrick', 'Jonathan', 'Bijan', 'Breece', 'Saquon', 'Tony', 'Jahmyr', 'Rachaad',
  'Tyreek', 'Ja\'Marr', 'Amon-Ra', 'CeeDee', 'Davante', 'Stefon', 'AJ', 'DeVonta',
  'Travis', 'George', 'TJ', 'Myles', 'Micah', 'Fred', 'Roquan', 'Sauce',
];

const MOCK_LAST_NAMES = [
  'Mahomes', 'Allen', 'Jackson', 'Herbert', 'Burrow', 'Tagovailoa', 'Lawrence', 'Hurts',
  'Henry', 'Taylor', 'Robinson', 'Hall', 'Barkley', 'Pollard', 'Gibbs', 'White',
  'Hill', 'Chase', 'St. Brown', 'Lamb', 'Adams', 'Diggs', 'Brown', 'Smith',
  'Kelce', 'Kittle', 'Watt', 'Garrett', 'Parsons', 'Warner', 'Smith', 'Gardner',
];

function generateMockName(): string {
  const first = MOCK_FIRST_NAMES[randomInt(0, MOCK_FIRST_NAMES.length - 1)];
  const last = MOCK_LAST_NAMES[randomInt(0, MOCK_LAST_NAMES.length - 1)];
  return `${first} ${last}`;
}

export function generateMockLeagueLeaders(
  category: StatCategory,
  stat: string,
  count: number = 10
): LeagueLeader[] {
  const leaders: LeagueLeader[] = [];

  // Top value configs by stat
  const topValues: Record<string, { top: number; dropoff: number; position: string }> = {
    'passing.yards': { top: 5200, dropoff: 150, position: 'QB' },
    'passing.touchdowns': { top: 48, dropoff: 2, position: 'QB' },
    'passing.passer_rating': { top: 118, dropoff: 2, position: 'QB' },
    'rushing.yards': { top: 1800, dropoff: 80, position: 'RB' },
    'rushing.touchdowns': { top: 18, dropoff: 1, position: 'RB' },
    'receiving.yards': { top: 1600, dropoff: 70, position: 'WR' },
    'receiving.receptions': { top: 125, dropoff: 5, position: 'WR' },
    'receiving.touchdowns': { top: 14, dropoff: 1, position: 'WR' },
    'defense.sacks': { top: 18, dropoff: 0.8, position: 'DE' },
    'defense.interceptions': { top: 8, dropoff: 0.4, position: 'CB' },
    'defense.tackles': { top: 165, dropoff: 5, position: 'LB' },
  };

  const key = `${category}.${stat}`;
  const config = topValues[key] || { top: 100, dropoff: 5, position: 'QB' };

  for (let i = 0; i < count; i++) {
    const variance = randomInRange(-config.dropoff * 0.5, config.dropoff * 0.5);
    const value = config.top - i * config.dropoff + variance;

    leaders.push({
      rank: i + 1,
      player_id: `mock_leader_${i}`,
      player_name: generateMockName(),
      team_abbr: MOCK_TEAM_ABBRS[randomInt(0, MOCK_TEAM_ABBRS.length - 1)],
      position: config.position,
      value: Math.round(value * 10) / 10,
      games_played: randomInt(14, 17),
    });
  }

  return leaders;
}

export function generateMockLeagueLeadersCategories(): LeagueLeadersCategory[] {
  return [
    {
      category: 'passing',
      stat: 'yards',
      stat_label: 'Passing Yards',
      leaders: generateMockLeagueLeaders('passing', 'yards'),
    },
    {
      category: 'passing',
      stat: 'touchdowns',
      stat_label: 'Passing TDs',
      leaders: generateMockLeagueLeaders('passing', 'touchdowns'),
    },
    {
      category: 'rushing',
      stat: 'yards',
      stat_label: 'Rushing Yards',
      leaders: generateMockLeagueLeaders('rushing', 'yards'),
    },
    {
      category: 'rushing',
      stat: 'touchdowns',
      stat_label: 'Rushing TDs',
      leaders: generateMockLeagueLeaders('rushing', 'touchdowns'),
    },
    {
      category: 'receiving',
      stat: 'yards',
      stat_label: 'Receiving Yards',
      leaders: generateMockLeagueLeaders('receiving', 'yards'),
    },
    {
      category: 'receiving',
      stat: 'receptions',
      stat_label: 'Receptions',
      leaders: generateMockLeagueLeaders('receiving', 'receptions'),
    },
    {
      category: 'defense',
      stat: 'sacks',
      stat_label: 'Sacks',
      leaders: generateMockLeagueLeaders('defense', 'sacks'),
    },
    {
      category: 'defense',
      stat: 'interceptions',
      stat_label: 'Interceptions',
      leaders: generateMockLeagueLeaders('defense', 'interceptions'),
    },
  ];
}
