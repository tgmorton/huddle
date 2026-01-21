"""
Commentary Generator

Implementation of CommentaryGenerator using Gemini Flash API.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from .client import GeminiClient, GenerationResult, GeminiClientError
from .prompts import build_play_by_play_prompt, build_color_prompt
from .schema import CommentaryContext, CommentaryGenerator


logger = logging.getLogger(__name__)


@dataclass
class CommentaryResult:
    """Extended result with metadata for monitoring."""
    text: str
    latency_ms: float
    tokens_used: int
    model: str


class GeminiCommentaryGenerator(CommentaryGenerator):
    """
    Commentary generator using Gemini Flash API.

    Implements the CommentaryGenerator interface for generating
    play-by-play and color commentary.

    Usage:
        generator = GeminiCommentaryGenerator()
        play_by_play = await generator.generate_play_by_play(context)
        color = await generator.generate_color(context)
    """

    # Generation parameters
    PLAY_BY_PLAY_TEMP = 0.7      # Slightly lower for factual accuracy
    PLAY_BY_PLAY_MAX_TOKENS = 100  # Short, punchy calls
    COLOR_TEMP = 0.85            # Higher for creative variety
    COLOR_MAX_TOKENS = 200       # Longer for narrative

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize the generator.

        Args:
            api_key: Gemini API key. Defaults to GEMINI_API_KEY env var.
            model: Model to use. Defaults to gemini-2.0-flash-exp.
        """
        self._client = GeminiClient(api_key=api_key, model=model)
        self._last_play_by_play: Optional[str] = None

    async def close(self):
        """Close the underlying client."""
        await self._client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def generate_play_by_play(
        self,
        context: CommentaryContext,
    ) -> str:
        """
        Generate play-by-play commentary.

        Quick, reactive description of what just happened.
        Targets < 1.5 seconds latency.

        Args:
            context: Full commentary context.

        Returns:
            Play-by-play call (1-2 sentences).
        """
        system_prompt, user_prompt = build_play_by_play_prompt(context)

        try:
            result = await self._client.generate(
                system=system_prompt,
                user=user_prompt,
                temperature=self.PLAY_BY_PLAY_TEMP,
                max_tokens=self.PLAY_BY_PLAY_MAX_TOKENS,
            )

            text = result.text.strip()
            self._last_play_by_play = text

            logger.debug(
                f"Play-by-play generated: {result.latency_ms:.0f}ms, "
                f"{result.total_tokens} tokens"
            )

            return text

        except GeminiClientError as e:
            logger.error(f"Failed to generate play-by-play: {e}")
            # Fallback to basic description
            return self._fallback_play_by_play(context)

    async def generate_color(
        self,
        context: CommentaryContext,
    ) -> str:
        """
        Generate color commentary.

        Narrative-rich insight building on the play-by-play.
        Targets < 3 seconds latency.

        Args:
            context: Full commentary context.

        Returns:
            Color commentary (2-4 sentences).
        """
        # Use cached play-by-play or generate one
        play_by_play = self._last_play_by_play
        if not play_by_play:
            play_by_play = await self.generate_play_by_play(context)

        system_prompt, user_prompt = build_color_prompt(context, play_by_play)

        try:
            result = await self._client.generate(
                system=system_prompt,
                user=user_prompt,
                temperature=self.COLOR_TEMP,
                max_tokens=self.COLOR_MAX_TOKENS,
            )

            text = result.text.strip()

            logger.debug(
                f"Color commentary generated: {result.latency_ms:.0f}ms, "
                f"{result.total_tokens} tokens"
            )

            return text

        except GeminiClientError as e:
            logger.error(f"Failed to generate color commentary: {e}")
            return self._fallback_color(context)

    async def generate_both(
        self,
        context: CommentaryContext,
    ) -> tuple[str, str]:
        """
        Generate both play-by-play and color commentary.

        Convenience method that generates both in sequence,
        using the play-by-play output for color context.

        Args:
            context: Full commentary context.

        Returns:
            tuple[str, str]: (play_by_play, color)
        """
        play_by_play = await self.generate_play_by_play(context)
        color = await self.generate_color(context)
        return play_by_play, color

    async def generate_play_by_play_with_metadata(
        self,
        context: CommentaryContext,
    ) -> CommentaryResult:
        """Generate play-by-play with full metadata for monitoring."""
        system_prompt, user_prompt = build_play_by_play_prompt(context)

        result = await self._client.generate(
            system=system_prompt,
            user=user_prompt,
            temperature=self.PLAY_BY_PLAY_TEMP,
            max_tokens=self.PLAY_BY_PLAY_MAX_TOKENS,
        )

        text = result.text.strip()
        self._last_play_by_play = text

        return CommentaryResult(
            text=text,
            latency_ms=result.latency_ms,
            tokens_used=result.total_tokens,
            model=result.model,
        )

    async def generate_color_with_metadata(
        self,
        context: CommentaryContext,
    ) -> CommentaryResult:
        """Generate color commentary with full metadata for monitoring."""
        play_by_play = self._last_play_by_play
        if not play_by_play:
            play_by_play = await self.generate_play_by_play(context)

        system_prompt, user_prompt = build_color_prompt(context, play_by_play)

        result = await self._client.generate(
            system=system_prompt,
            user=user_prompt,
            temperature=self.COLOR_TEMP,
            max_tokens=self.COLOR_MAX_TOKENS,
        )

        return CommentaryResult(
            text=result.text.strip(),
            latency_ms=result.latency_ms,
            tokens_used=result.total_tokens,
            model=result.model,
        )

    def _fallback_play_by_play(self, context: CommentaryContext) -> str:
        """Generate basic fallback play-by-play without API."""
        play = context.play
        outcome = play.outcome

        if outcome == "complete":
            receiver = play.receiver
            name = receiver.name if receiver else "the receiver"
            return f"Pass complete to {name} for {play.yards_gained:.0f} yards."
        elif outcome == "incomplete":
            return "Pass incomplete."
        elif outcome == "sack":
            return f"Sack! Loss of {abs(play.yards_gained):.0f} yards."
        elif outcome == "interception":
            return "Intercepted!"
        elif play.play_concept.play_type == "run":
            carrier = play.ball_carrier
            name = carrier.name if carrier else "the runner"
            return f"Handoff to {name} for {play.yards_gained:.0f} yards."
        else:
            return f"Play results in {play.yards_gained:.0f} yards."

    def _fallback_color(self, context: CommentaryContext) -> str:
        """Generate basic fallback color commentary without API."""
        play = context.play
        sit = play.situation

        if play.resulted_in_touchdown:
            return "And that's six! What a play to find the end zone."
        elif play.was_explosive:
            return "A big-time play there. That changes the complexion of this drive."
        elif play.resulted_in_turnover:
            return "That's a crucial turnover. Momentum shift right there."
        elif sit.is_red_zone:
            return "They're knocking on the door now in the red zone."
        elif sit.is_two_minute_warning:
            return "Clock management is critical here."
        else:
            return ""

    @property
    def total_tokens_used(self) -> int:
        """Total tokens used across all requests."""
        return self._client.total_tokens_used

    @property
    def request_count(self) -> int:
        """Total requests made."""
        return self._client.request_count
