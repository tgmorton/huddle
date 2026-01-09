// PlayoffsContent.tsx - Playoff picture and bracket visualization

import React, { useEffect, useState, useCallback } from 'react';
import { Trophy, Star, ChevronRight } from 'lucide-react';
import { adminApi } from '../../../api/adminClient';
import type { PlayoffPicture, PlayoffBracket, PlayoffTeam, PlayoffBracketGame } from '../../../types/admin';
import { useManagementStore } from '../../../stores/managementStore';

// === Helper Components ===

interface SeedBadgeProps {
  seed: number;
  isDivisionWinner: boolean;
}

const SeedBadge: React.FC<SeedBadgeProps> = ({ seed, isDivisionWinner }) => (
  <span className={`playoffs__seed ${isDivisionWinner ? 'playoffs__seed--division' : ''}`}>
    {seed}
  </span>
);

interface TeamRowProps {
  team: PlayoffTeam;
  isUserTeam: boolean;
}

const TeamRow: React.FC<TeamRowProps> = ({ team, isUserTeam }) => (
  <div className={`playoffs__team ${isUserTeam ? 'playoffs__team--you' : ''}`}>
    <SeedBadge seed={team.seed} isDivisionWinner={team.is_division_winner} />
    <span className="playoffs__team-name">{team.team_name}</span>
    <span className="playoffs__record">{team.record}</span>
    {team.is_division_winner && <Star size={12} className="playoffs__division-icon" />}
  </div>
);

interface BracketGameProps {
  game: PlayoffBracketGame;
  userTeamAbbr?: string;
}

const BracketGame: React.FC<BracketGameProps> = ({ game, userTeamAbbr }) => {
  const isUserGame = game.home_team === userTeamAbbr || game.away_team === userTeamAbbr;

  if (!game.home_team && !game.away_team) {
    return (
      <div className="bracket-game bracket-game--tbd">
        <div className="bracket-game__matchup">
          <span className="bracket-game__team bracket-game__team--tbd">TBD</span>
          <span className="bracket-game__vs">vs</span>
          <span className="bracket-game__team bracket-game__team--tbd">TBD</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`bracket-game ${isUserGame ? 'bracket-game--user' : ''} ${game.is_played ? 'bracket-game--played' : ''}`}>
      <div className="bracket-game__matchup">
        <span className={`bracket-game__team ${game.winner === game.away_team ? 'bracket-game__team--winner' : ''}`}>
          {game.away_team || 'TBD'}
          {game.is_played && <span className="bracket-game__score">{game.away_score}</span>}
        </span>
        <span className="bracket-game__at">@</span>
        <span className={`bracket-game__team ${game.winner === game.home_team ? 'bracket-game__team--winner' : ''}`}>
          {game.home_team || 'TBD'}
          {game.is_played && <span className="bracket-game__score">{game.home_score}</span>}
        </span>
      </div>
      {game.is_played && game.winner && (
        <div className="bracket-game__result">
          <ChevronRight size={12} />
          <span>{game.winner} advances</span>
        </div>
      )}
    </div>
  );
};

interface BracketRoundProps {
  title: string;
  games: PlayoffBracketGame[];
  userTeamAbbr?: string;
}

const BracketRound: React.FC<BracketRoundProps> = ({ title, games, userTeamAbbr }) => (
  <div className="bracket-round">
    <div className="bracket-round__header">{title}</div>
    <div className="bracket-round__games">
      {games.map((game, i) => (
        <BracketGame key={game.game_id || i} game={game} userTeamAbbr={userTeamAbbr} />
      ))}
    </div>
  </div>
);

// === Main Component ===

export const PlayoffsContent: React.FC = () => {
  const [picture, setPicture] = useState<PlayoffPicture | null>(null);
  const [bracket, setBracket] = useState<PlayoffBracket | null>(null);
  const [loading, setLoading] = useState(true);
  const [userTeamAbbr, setUserTeamAbbr] = useState<string | undefined>();

  const { state, calendar } = useManagementStore();
  const isPlayoffs = calendar?.phase?.startsWith('WILD') ||
    calendar?.phase?.startsWith('DIVISIONAL') ||
    calendar?.phase?.startsWith('CONFERENCE') ||
    calendar?.phase?.startsWith('SUPER');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [pictureData, bracketData] = await Promise.all([
        adminApi.getPlayoffPicture(),
        adminApi.getPlayoffBracket(),
      ]);
      setPicture(pictureData);
      setBracket(bracketData);
    } catch (err) {
      console.error('Failed to load playoff data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Get user team abbreviation
  useEffect(() => {
    if (state?.player_team_id) {
      adminApi.listTeams().then(teams => {
        const team = teams.find(t => t.id === state.player_team_id);
        if (team) {
          setUserTeamAbbr(team.abbreviation);
        }
      }).catch(() => {});
    }
  }, [state?.player_team_id]);

  if (loading) {
    return <div className="ref-content playoffs-content">Loading...</div>;
  }

  // Show bracket if in playoffs or if bracket has played games
  const showBracket = isPlayoffs || (bracket && (
    bracket.wild_card.some(g => g.is_played) ||
    bracket.divisional.some(g => g.is_played) ||
    bracket.conference.some(g => g.is_played) ||
    bracket.super_bowl?.is_played
  ));

  return (
    <div className="ref-content playoffs-content">
      {/* Champion Banner */}
      {bracket?.champion && (
        <div className="playoffs__champion">
          <Trophy size={20} />
          <span>{bracket.champion} - Super Bowl Champions</span>
        </div>
      )}

      {/* Playoff Picture (Seeding) */}
      {picture && !showBracket && (
        <>
          <div className="playoffs__conference">
            <div className="playoffs__conference-header">AFC</div>
            {picture.afc.map(team => (
              <TeamRow
                key={team.abbreviation}
                team={team}
                isUserTeam={team.abbreviation === userTeamAbbr}
              />
            ))}
          </div>
          <div className="playoffs__conference">
            <div className="playoffs__conference-header">NFC</div>
            {picture.nfc.map(team => (
              <TeamRow
                key={team.abbreviation}
                team={team}
                isUserTeam={team.abbreviation === userTeamAbbr}
              />
            ))}
          </div>
        </>
      )}

      {/* Playoff Bracket */}
      {bracket && showBracket && (
        <div className="playoffs__bracket">
          <BracketRound
            title="Wild Card"
            games={bracket.wild_card}
            userTeamAbbr={userTeamAbbr}
          />
          <BracketRound
            title="Divisional"
            games={bracket.divisional}
            userTeamAbbr={userTeamAbbr}
          />
          <BracketRound
            title="Conference"
            games={bracket.conference}
            userTeamAbbr={userTeamAbbr}
          />
          {bracket.super_bowl && (
            <div className="bracket-round bracket-round--super-bowl">
              <div className="bracket-round__header">
                <Trophy size={14} /> Super Bowl
              </div>
              <BracketGame game={bracket.super_bowl} userTeamAbbr={userTeamAbbr} />
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!picture && !bracket && (
        <div className="playoffs__empty">
          <p>Playoff picture will appear as the season progresses.</p>
        </div>
      )}
    </div>
  );
};

export default PlayoffsContent;
