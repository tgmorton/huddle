/**
 * ScoreBug Lab - Interactive scorebug prototypes
 *
 * Three broadcast styles:
 * - CBS: Clean, boxy design with logos on edges
 * - ESPN: Horizontal bar with prominent play clock
 * - NBC: Sleek curved design with gradient team colors
 */

import { useState, useEffect, useRef } from 'react';
import './ScoreBugLab.css';

interface GameState {
  homeTeam: TeamInfo;
  awayTeam: TeamInfo;
  quarter: number;
  gameClockSeconds: number;
  playClockSeconds: number;
  down: number;
  distance: number;
  ballOn: number;
  possession: 'home' | 'away';
}

interface TeamInfo {
  abbrev: string;
  name: string;
  score: number;
  record: string;
  timeouts: number;
  color: string;
  colorAlt: string;
  logo: string;
}

// All 32 NFL teams with official colors and logos
const TEAMS: Record<string, TeamInfo> = {
  ARI: { abbrev: 'ARI', name: 'Cardinals', score: 0, record: '4-7', timeouts: 3, color: '#97233F', colorAlt: '#000000', logo: '/logos/Arizona_Cardinals_logo.svg' },
  ATL: { abbrev: 'ATL', name: 'Falcons', score: 0, record: '6-5', timeouts: 3, color: '#A71930', colorAlt: '#000000', logo: '/logos/Atlanta_Falcons_logo.svg' },
  BAL: { abbrev: 'BAL', name: 'Ravens', score: 0, record: '8-3', timeouts: 3, color: '#241773', colorAlt: '#000000', logo: '/logos/Baltimore_Ravens_logo.svg' },
  BUF: { abbrev: 'BUF', name: 'Bills', score: 0, record: '9-2', timeouts: 3, color: '#00338D', colorAlt: '#C60C30', logo: '/logos/Buffalo_Bills_logo.svg' },
  CAR: { abbrev: 'CAR', name: 'Panthers', score: 0, record: '3-8', timeouts: 3, color: '#0085CA', colorAlt: '#101820', logo: '/logos/Carolina_Panthers_logo.svg' },
  CHI: { abbrev: 'CHI', name: 'Bears', score: 0, record: '4-7', timeouts: 3, color: '#0B162A', colorAlt: '#C83803', logo: '/logos/Chicago_Bears_logo.svg' },
  CIN: { abbrev: 'CIN', name: 'Bengals', score: 0, record: '4-7', timeouts: 3, color: '#FB4F14', colorAlt: '#000000', logo: '/logos/Cincinnati_Bengals_logo.svg' },
  CLE: { abbrev: 'CLE', name: 'Browns', score: 0, record: '3-8', timeouts: 3, color: '#311D00', colorAlt: '#FF3C00', logo: '/logos/Cleveland_Browns_logo.svg' },
  DAL: { abbrev: 'DAL', name: 'Cowboys', score: 0, record: '5-6', timeouts: 3, color: '#003594', colorAlt: '#869397', logo: '/logos/Dallas_Cowboys_logo.svg' },
  DEN: { abbrev: 'DEN', name: 'Broncos', score: 0, record: '7-5', timeouts: 3, color: '#FB4F14', colorAlt: '#002244', logo: '/logos/Denver_Broncos_logo.svg' },
  DET: { abbrev: 'DET', name: 'Lions', score: 0, record: '10-1', timeouts: 3, color: '#0076B6', colorAlt: '#B0B7BC', logo: '/logos/Detroit_Lions_logo.svg' },
  GB: { abbrev: 'GB', name: 'Packers', score: 0, record: '8-3', timeouts: 3, color: '#203731', colorAlt: '#FFB612', logo: '/logos/Green_Bay_Packers_logo.svg' },
  HOU: { abbrev: 'HOU', name: 'Texans', score: 0, record: '7-5', timeouts: 3, color: '#03202F', colorAlt: '#A71930', logo: '/logos/Houston_Texans_logo.svg' },
  IND: { abbrev: 'IND', name: 'Colts', score: 0, record: '5-7', timeouts: 3, color: '#002C5F', colorAlt: '#A2AAAD', logo: '/logos/Indianapolis_Colts_logo.svg' },
  JAX: { abbrev: 'JAX', name: 'Jaguars', score: 0, record: '2-9', timeouts: 3, color: '#006778', colorAlt: '#D7A22A', logo: '/logos/Jacksonville_Jaguars_logo.svg' },
  KC: { abbrev: 'KC', name: 'Chiefs', score: 0, record: '10-1', timeouts: 3, color: '#E31837', colorAlt: '#FFB81C', logo: '/logos/Kansas_City_Chiefs_logo.svg' },
  LV: { abbrev: 'LV', name: 'Raiders', score: 0, record: '2-9', timeouts: 3, color: '#000000', colorAlt: '#A5ACAF', logo: '/logos/Las_Vegas_Raiders_logo.svg' },
  LAC: { abbrev: 'LAC', name: 'Chargers', score: 0, record: '7-4', timeouts: 3, color: '#0080C6', colorAlt: '#FFC20E', logo: '/logos/Los_Angeles_Chargers_logo.svg' },
  LAR: { abbrev: 'LAR', name: 'Rams', score: 0, record: '6-5', timeouts: 3, color: '#003594', colorAlt: '#FFA300', logo: '/logos/Los_Angeles_Rams_logo.svg' },
  MIA: { abbrev: 'MIA', name: 'Dolphins', score: 0, record: '5-6', timeouts: 3, color: '#008E97', colorAlt: '#FC4C02', logo: '/logos/Miami_Dolphins_logo.svg' },
  MIN: { abbrev: 'MIN', name: 'Vikings', score: 0, record: '9-2', timeouts: 3, color: '#4F2683', colorAlt: '#FFC62F', logo: '/logos/Minnesota_Vikings_logo.svg' },
  NE: { abbrev: 'NE', name: 'Patriots', score: 0, record: '3-9', timeouts: 3, color: '#002244', colorAlt: '#C60C30', logo: '/logos/New_England_Patriots_logo.svg' },
  NO: { abbrev: 'NO', name: 'Saints', score: 0, record: '4-7', timeouts: 3, color: '#D3BC8D', colorAlt: '#101820', logo: '/logos/New_Orleans_Saints_logo.svg' },
  NYG: { abbrev: 'NYG', name: 'Giants', score: 0, record: '2-9', timeouts: 3, color: '#0B2265', colorAlt: '#A71930', logo: '/logos/New_York_Giants_logo.svg' },
  NYJ: { abbrev: 'NYJ', name: 'Jets', score: 0, record: '3-8', timeouts: 3, color: '#125740', colorAlt: '#000000', logo: '/logos/New_York_Jets_logo.svg' },
  PHI: { abbrev: 'PHI', name: 'Eagles', score: 0, record: '9-2', timeouts: 3, color: '#004C54', colorAlt: '#A5ACAF', logo: '/logos/Philadelphia_Eagles_logo.svg' },
  PIT: { abbrev: 'PIT', name: 'Steelers', score: 0, record: '8-3', timeouts: 3, color: '#FFB612', colorAlt: '#101820', logo: '/logos/Pittsburgh_Steelers_logo.svg' },
  SF: { abbrev: 'SF', name: '49ers', score: 0, record: '5-6', timeouts: 3, color: '#AA0000', colorAlt: '#B3995D', logo: '/logos/San_Francisco_49ers_logo.svg' },
  SEA: { abbrev: 'SEA', name: 'Seahawks', score: 0, record: '6-5', timeouts: 3, color: '#002244', colorAlt: '#69BE28', logo: '/logos/Seattle_Seahawks_logo.svg' },
  TB: { abbrev: 'TB', name: 'Buccaneers', score: 0, record: '5-6', timeouts: 3, color: '#D50A0A', colorAlt: '#FF7900', logo: '/logos/Tampa_Bay_Buccaneers_logo.svg' },
  TEN: { abbrev: 'TEN', name: 'Titans', score: 0, record: '3-8', timeouts: 3, color: '#0C2340', colorAlt: '#4B92DB', logo: '/logos/Tennessee_Titans_logo.svg' },
  WAS: { abbrev: 'WAS', name: 'Commanders', score: 0, record: '7-5', timeouts: 3, color: '#5A1414', colorAlt: '#FFB612', logo: '/logos/Washington_Commanders_logo.svg' },
};

const DEFAULT_STATE: GameState = {
  homeTeam: { ...TEAMS.KC, score: 21, record: '10-1', timeouts: 2 },
  awayTeam: { ...TEAMS.BUF, score: 17, record: '9-2', timeouts: 3 },
  quarter: 2,
  gameClockSeconds: 8 * 60 + 37,
  playClockSeconds: 25,
  down: 1,
  distance: 10,
  ballOn: 35,
  possession: 'home',
};

// ============================================
// UTILITY FUNCTIONS
// ============================================

function formatClock(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function getOrdinalSuffix(num: number): string {
  if (num >= 11 && num <= 13) return 'TH';
  switch (num % 10) {
    case 1: return 'ST';
    case 2: return 'ND';
    case 3: return 'RD';
    default: return 'TH';
  }
}

function formatQuarter(quarter: number): string {
  if (quarter === 5) return 'OT';
  return `${quarter}${getOrdinalSuffix(quarter)}`;
}

function formatDownDistance(down: number, distance: number): string {
  return `${down}${getOrdinalSuffix(down)} & ${distance}`;
}

// ============================================
// CBS STYLE SCOREBUG
// ============================================
function CBSScoreBug({ game, awayScoreAnim, homeScoreAnim }: { game: GameState; awayScoreAnim: boolean; homeScoreAnim: boolean }) {
  return (
    <div className="scorebug cbs">
      <div className="cbs-down-distance">{formatDownDistance(game.down, game.distance)}</div>
      <div className="cbs-main">
        <div className="cbs-team away">
          <div className="cbs-logo">
            <img src={game.awayTeam.logo} alt={game.awayTeam.name} />
          </div>
          <span className={`cbs-score ${awayScoreAnim ? 'score-pop' : ''}`}>{game.awayTeam.score}</span>
          <div className="cbs-team-info">
            <span className="cbs-record">{game.awayTeam.record}</span>
            <div className="cbs-timeouts">
              {[...Array(3)].map((_, i) => (
                <span key={i} className={`timeout ${i < game.awayTeam.timeouts ? 'active' : ''}`} />
              ))}
            </div>
          </div>
          {game.possession === 'away' && <span className="cbs-possession">◀</span>}
        </div>

        <div className="cbs-clock">
          <span className="cbs-time">{formatClock(game.gameClockSeconds)}</span>
          <span className="cbs-quarter">{formatQuarter(game.quarter)}</span>
        </div>

        <div className="cbs-team home">
          {game.possession === 'home' && <span className="cbs-possession">▶</span>}
          <div className="cbs-team-info">
            <div className="cbs-timeouts">
              {[...Array(3)].map((_, i) => (
                <span key={i} className={`timeout ${i < game.homeTeam.timeouts ? 'active' : ''}`} />
              ))}
            </div>
            <span className="cbs-record">{game.homeTeam.record}</span>
          </div>
          <span className={`cbs-score ${homeScoreAnim ? 'score-pop' : ''}`}>{game.homeTeam.score}</span>
          <div className="cbs-logo">
            <img src={game.homeTeam.logo} alt={game.homeTeam.name} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// ESPN STYLE SCOREBUG
// ============================================
function ESPNScoreBug({ game, awayScoreAnim, homeScoreAnim }: { game: GameState; awayScoreAnim: boolean; homeScoreAnim: boolean }) {
  const isPlayClockLow = game.playClockSeconds <= 5;

  return (
    <div className="scorebug espn">
      <div className="espn-team away" style={{ background: game.awayTeam.color }}>
        <div className="espn-logo-circle">
          <img src={game.awayTeam.logo} alt={game.awayTeam.name} />
        </div>
        <span className={`espn-score ${awayScoreAnim ? 'score-pop' : ''}`}>{game.awayTeam.score}</span>
        <span className="espn-team-name">{game.awayTeam.abbrev}</span>
        {game.possession === 'away' && <span className="espn-possession">◀</span>}
        <div className="espn-timeouts">
          {[...Array(3)].map((_, i) => (
            <span key={i} className={`timeout ${i < game.awayTeam.timeouts ? 'active' : ''}`} />
          ))}
        </div>
      </div>

      <div className="espn-center">
        <div className="espn-down-distance">{formatDownDistance(game.down, game.distance)}</div>
        <div className="espn-clock-row">
          <span className="espn-quarter">{formatQuarter(game.quarter)}</span>
          <span className="espn-divider">|</span>
          <span className="espn-time">{formatClock(game.gameClockSeconds)}</span>
          <span className={`espn-play-clock ${isPlayClockLow ? 'low' : ''}`}>
            {game.playClockSeconds}
          </span>
        </div>
      </div>

      <div className="espn-team home" style={{ background: game.homeTeam.color }}>
        <div className="espn-timeouts">
          {[...Array(3)].map((_, i) => (
            <span key={i} className={`timeout ${i < game.homeTeam.timeouts ? 'active' : ''}`} />
          ))}
        </div>
        {game.possession === 'home' && <span className="espn-possession">▶</span>}
        <span className="espn-team-name">{game.homeTeam.abbrev}</span>
        <span className={`espn-score ${homeScoreAnim ? 'score-pop' : ''}`}>{game.homeTeam.score}</span>
        <div className="espn-logo-circle">
          <img src={game.homeTeam.logo} alt={game.homeTeam.name} />
        </div>
      </div>
    </div>
  );
}

// ============================================
// NBC STYLE SCOREBUG
// ============================================
function NBCScoreBug({ game, awayScoreAnim, homeScoreAnim }: { game: GameState; awayScoreAnim: boolean; homeScoreAnim: boolean }) {
  const isPlayClockLow = game.playClockSeconds <= 5;

  return (
    <div className="scorebug nbc">
      <div className="nbc-wing away" style={{ background: `linear-gradient(90deg, ${game.awayTeam.color} 0%, ${game.awayTeam.color}cc 100%)` }}>
        <div className="nbc-logo-container">
          <img src={game.awayTeam.logo} alt={game.awayTeam.name} />
        </div>
        <div className="nbc-team-info">
          <span className="nbc-abbrev">{game.awayTeam.abbrev}</span>
          <span className="nbc-record">{game.awayTeam.record}</span>
        </div>
        <span className={`nbc-score ${awayScoreAnim ? 'score-pop' : ''}`}>{game.awayTeam.score}</span>
        {game.possession === 'away' && <span className="nbc-possession">◀</span>}
        <div className="nbc-timeouts">
          {[...Array(3)].map((_, i) => (
            <span key={i} className={`timeout ${i < game.awayTeam.timeouts ? 'active' : ''}`} />
          ))}
        </div>
      </div>

      <div className="nbc-center">
        <div className="nbc-network-logo">
          <span>NBC</span>
        </div>
        <div className="nbc-clock-container">
          <span className="nbc-time">{formatClock(game.gameClockSeconds)}</span>
          <div className="nbc-clock-bottom">
            <span className="nbc-quarter">{formatQuarter(game.quarter)}</span>
            <span className={`nbc-play-clock ${isPlayClockLow ? 'low' : ''}`}>{game.playClockSeconds}</span>
          </div>
        </div>
      </div>

      <div className="nbc-wing home" style={{ background: `linear-gradient(90deg, ${game.homeTeam.color}cc 0%, ${game.homeTeam.color} 100%)` }}>
        <div className="nbc-timeouts right">
          {[...Array(3)].map((_, i) => (
            <span key={i} className={`timeout ${i < game.homeTeam.timeouts ? 'active' : ''}`} />
          ))}
        </div>
        {game.possession === 'home' && <span className="nbc-possession">▶</span>}
        <span className={`nbc-score ${homeScoreAnim ? 'score-pop' : ''}`}>{game.homeTeam.score}</span>
        <div className="nbc-team-info right">
          <span className="nbc-abbrev">{game.homeTeam.abbrev}</span>
          <span className="nbc-record">{game.homeTeam.record}</span>
        </div>
        <div className="nbc-logo-container">
          <img src={game.homeTeam.logo} alt={game.homeTeam.name} />
        </div>
      </div>

      <div className="nbc-down-tail">
        <span>{formatDownDistance(game.down, game.distance)}</span>
      </div>
    </div>
  );
}

// ============================================
// SNF (SUNDAY NIGHT FOOTBALL) STYLE SCOREBUG
// ============================================
function SNFScoreBug({ game, awayScoreAnim, homeScoreAnim }: { game: GameState; awayScoreAnim: boolean; homeScoreAnim: boolean }) {
  const isPlayClockLow = game.playClockSeconds <= 5;

  return (
    <div className="scorebug snf">
      <div className="snf-main">
        {/* Away Wing */}
        <div className="snf-wing away">
          <div className="snf-wing-bg" style={{ background: `linear-gradient(180deg, ${game.awayTeam.color} 0%, ${game.awayTeam.color}aa 100%)` }} />
          <div className="snf-wing-content">
            <img className="snf-logo" src={game.awayTeam.logo} alt={game.awayTeam.name} />
            <div className="snf-team-abbrev">
              <sup className="snf-rank">5</sup>
              {game.awayTeam.abbrev}
            </div>
            <span className={`snf-score ${awayScoreAnim ? 'score-pop' : ''}`}>{game.awayTeam.score}</span>
            {game.possession === 'away' && <span className="snf-possession">◀</span>}
            <div className="snf-timeouts">
              {[...Array(3)].map((_, i) => (
                <span key={i} className={`timeout ${i < game.awayTeam.timeouts ? 'active' : ''}`} />
              ))}
            </div>
          </div>
        </div>

        {/* Center Circle */}
        <div className="snf-center">
          <div className="snf-peacock">❋</div>
          <div className="snf-clock">{formatClock(game.gameClockSeconds)}</div>
          <div className="snf-clock-row">
            <span className="snf-quarter">{formatQuarter(game.quarter)}</span>
            <span className={`snf-play-clock ${isPlayClockLow ? 'low' : ''}`}>{game.playClockSeconds}</span>
          </div>
        </div>

        {/* Home Wing */}
        <div className="snf-wing home">
          <div className="snf-wing-bg" style={{ background: `linear-gradient(180deg, ${game.homeTeam.color} 0%, ${game.homeTeam.color}aa 100%)` }} />
          <div className="snf-wing-content">
            <div className="snf-timeouts right">
              {[...Array(3)].map((_, i) => (
                <span key={i} className={`timeout ${i < game.homeTeam.timeouts ? 'active' : ''}`} />
              ))}
            </div>
            {game.possession === 'home' && <span className="snf-possession">▶</span>}
            <span className={`snf-score ${homeScoreAnim ? 'score-pop' : ''}`}>{game.homeTeam.score}</span>
            <div className="snf-team-abbrev">
              <sup className="snf-rank">2</sup>
              {game.homeTeam.abbrev}
            </div>
            <img className="snf-logo" src={game.homeTeam.logo} alt={game.homeTeam.name} />
          </div>
        </div>
      </div>

      {/* Down & Distance Bar - Separate Element */}
      <div className="snf-down-bar" style={{ background: `linear-gradient(180deg, ${game.awayTeam.color}cc 0%, ${game.awayTeam.color}88 100%)` }}>
        <span className="snf-down-arrow">▶</span>
        <span className="snf-down-text">{formatDownDistance(game.down, game.distance)}</span>
        <span className="snf-down-arrow">▶</span>
      </div>
    </div>
  );
}

// ============================================
// MAIN LAB COMPONENT
// ============================================
export function ScoreBugLab() {
  const [game, setGame] = useState<GameState>(DEFAULT_STATE);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedStyle, setSelectedStyle] = useState<'all' | 'cbs' | 'espn' | 'nbc' | 'snf'>('all');

  // Score animation tracking
  const [awayScoreAnim, setAwayScoreAnim] = useState(false);
  const [homeScoreAnim, setHomeScoreAnim] = useState(false);
  const prevAwayScore = useRef(game.awayTeam.score);
  const prevHomeScore = useRef(game.homeTeam.score);

  // Detect score changes and trigger animation
  useEffect(() => {
    if (game.awayTeam.score !== prevAwayScore.current) {
      setAwayScoreAnim(true);
      setTimeout(() => setAwayScoreAnim(false), 600);
      prevAwayScore.current = game.awayTeam.score;
    }
  }, [game.awayTeam.score]);

  useEffect(() => {
    if (game.homeTeam.score !== prevHomeScore.current) {
      setHomeScoreAnim(true);
      setTimeout(() => setHomeScoreAnim(false), 600);
      prevHomeScore.current = game.homeTeam.score;
    }
  }, [game.homeTeam.score]);

  // Simulate clock ticking
  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      setGame(prev => {
        const newPlayClock = prev.playClockSeconds - 1;
        const newGameClock = newPlayClock <= 0 ? prev.gameClockSeconds - 1 : prev.gameClockSeconds;

        return {
          ...prev,
          gameClockSeconds: Math.max(0, newGameClock),
          playClockSeconds: newPlayClock <= 0 ? 40 : newPlayClock,
        };
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isRunning]);

  const addScore = (team: 'home' | 'away', points: number) => {
    setGame(prev => ({
      ...prev,
      [team === 'home' ? 'homeTeam' : 'awayTeam']: {
        ...prev[team === 'home' ? 'homeTeam' : 'awayTeam'],
        score: prev[team === 'home' ? 'homeTeam' : 'awayTeam'].score + points,
      },
      possession: team === 'home' ? 'away' : 'home', // Possession changes after score
    }));
  };

  const cycleDown = () => {
    setGame(prev => ({
      ...prev,
      down: prev.down >= 4 ? 1 : prev.down + 1,
      distance: prev.down >= 4 ? 10 : Math.max(1, prev.distance - 3),
    }));
  };

  const togglePossession = () => {
    setGame(prev => ({
      ...prev,
      possession: prev.possession === 'home' ? 'away' : 'home',
    }));
  };

  const useTimeout = (team: 'home' | 'away') => {
    setGame(prev => ({
      ...prev,
      [team === 'home' ? 'homeTeam' : 'awayTeam']: {
        ...prev[team === 'home' ? 'homeTeam' : 'awayTeam'],
        timeouts: Math.max(0, prev[team === 'home' ? 'homeTeam' : 'awayTeam'].timeouts - 1),
      },
    }));
  };

  const changeTeams = () => {
    const teamKeys = Object.keys(TEAMS);
    const randomAway = TEAMS[teamKeys[Math.floor(Math.random() * teamKeys.length)]];
    let randomHome = TEAMS[teamKeys[Math.floor(Math.random() * teamKeys.length)]];
    while (randomHome.abbrev === randomAway.abbrev) {
      randomHome = TEAMS[teamKeys[Math.floor(Math.random() * teamKeys.length)]];
    }
    const newAwayScore = Math.floor(Math.random() * 35);
    const newHomeScore = Math.floor(Math.random() * 35);
    prevAwayScore.current = newAwayScore;
    prevHomeScore.current = newHomeScore;
    setGame(prev => ({
      ...prev,
      awayTeam: { ...randomAway, score: newAwayScore, timeouts: Math.floor(Math.random() * 4) },
      homeTeam: { ...randomHome, score: newHomeScore, timeouts: Math.floor(Math.random() * 4) },
    }));
  };

  return (
    <div className="scorebug-lab">
      <div className="lab-title">
        <h2>Score Bug Prototypes</h2>
        <p>Three broadcast styles - CBS, ESPN, NBC</p>
      </div>

      <div className="style-selector">
        <button className={selectedStyle === 'all' ? 'active' : ''} onClick={() => setSelectedStyle('all')}>All</button>
        <button className={selectedStyle === 'cbs' ? 'active' : ''} onClick={() => setSelectedStyle('cbs')}>CBS</button>
        <button className={selectedStyle === 'espn' ? 'active' : ''} onClick={() => setSelectedStyle('espn')}>ESPN</button>
        <button className={selectedStyle === 'nbc' ? 'active' : ''} onClick={() => setSelectedStyle('nbc')}>NBC</button>
        <button className={selectedStyle === 'snf' ? 'active' : ''} onClick={() => setSelectedStyle('snf')}>SNF</button>
      </div>

      <div className="scorebugs-display">
        {(selectedStyle === 'all' || selectedStyle === 'cbs') && (
          <div className="scorebug-wrapper">
            <span className="style-label">CBS</span>
            <CBSScoreBug game={game} awayScoreAnim={awayScoreAnim} homeScoreAnim={homeScoreAnim} />
          </div>
        )}
        {(selectedStyle === 'all' || selectedStyle === 'espn') && (
          <div className="scorebug-wrapper">
            <span className="style-label">ESPN</span>
            <ESPNScoreBug game={game} awayScoreAnim={awayScoreAnim} homeScoreAnim={homeScoreAnim} />
          </div>
        )}
        {(selectedStyle === 'all' || selectedStyle === 'nbc') && (
          <div className="scorebug-wrapper">
            <span className="style-label">NBC</span>
            <NBCScoreBug game={game} awayScoreAnim={awayScoreAnim} homeScoreAnim={homeScoreAnim} />
          </div>
        )}
        {(selectedStyle === 'all' || selectedStyle === 'snf') && (
          <div className="scorebug-wrapper">
            <span className="style-label">SNF (Sunday Night Football)</span>
            <SNFScoreBug game={game} awayScoreAnim={awayScoreAnim} homeScoreAnim={homeScoreAnim} />
          </div>
        )}
      </div>

      <div className="controls-panel">
        <div className="control-group">
          <h4>Simulation</h4>
          <button onClick={() => setIsRunning(!isRunning)}>
            {isRunning ? '⏸ Pause' : '▶ Run Clock'}
          </button>
          <button onClick={changeTeams}>🔀 Random Teams</button>
          <button onClick={togglePossession}>🏈 Flip Possession</button>
        </div>

        <div className="control-group">
          <h4>Away Team</h4>
          <button onClick={() => addScore('away', 7)}>+7 TD</button>
          <button onClick={() => addScore('away', 3)}>+3 FG</button>
          <button onClick={() => useTimeout('away')}>Use Timeout</button>
        </div>

        <div className="control-group">
          <h4>Home Team</h4>
          <button onClick={() => addScore('home', 7)}>+7 TD</button>
          <button onClick={() => addScore('home', 3)}>+3 FG</button>
          <button onClick={() => useTimeout('home')}>Use Timeout</button>
        </div>

        <div className="control-group">
          <h4>Game State</h4>
          <button onClick={cycleDown}>Next Down</button>
          <button onClick={() => setGame(prev => ({ ...prev, quarter: prev.quarter >= 4 ? 1 : prev.quarter + 1 }))}>Next Quarter</button>
        </div>
      </div>
    </div>
  );
}
