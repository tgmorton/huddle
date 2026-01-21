/**
 * GameView hooks - State management and API integration
 */

export { useCoachAPI } from './useCoachAPI';
export type { StartGameParams } from './useCoachAPI';
export { useGameWebSocket } from './useGameWebSocket';
export { useGameState } from './useGameState';
export type { UseGameStateReturn } from './useGameState';
export { gameStateReducer, initialGameState } from './gameStateReducer';
export type { GameState, GameAction, GamePanelView } from './gameStateReducer';
