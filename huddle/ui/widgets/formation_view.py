"""Formation display widget showing tactical card style diagrams."""

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from huddle.core.enums import DefensiveScheme, Formation, PersonnelPackage
from huddle.core.models.player import Player
from huddle.core.models.team import Team


# === Styling Constants ===
# Position group styles for Rich Text
STYLE_OLINE = "bold white on #1565c0"      # Blue blocks - heavy/solid
STYLE_OLINE_LABEL = "bold #1565c0"          # Blue text for labels
STYLE_WR = "bold #00bcd4"                   # Cyan - speed/route runners
STYLE_TE = "bold #9c27b0"                   # Purple - hybrid
STYLE_QB = "bold #ffc107"                   # Gold/Yellow - star
STYLE_RB = "bold #4caf50"                   # Green - power/speed
STYLE_FB = "bold #8bc34a"                   # Light green - blocking back

# Defense styles
STYLE_DLINE = "bold white on #c62828"       # Red blocks - aggression
STYLE_DLINE_LABEL = "bold #c62828"          # Red text
STYLE_LB = "bold #ff9800"                   # Orange - versatile
STYLE_CB = "bold #2196f3"                   # Blue - coverage
STYLE_SAFETY = "bold #673ab7"               # Deep purple - last line

# Structural styles
STYLE_BORDER = "dim #888888"
STYLE_LOS = "bold #ffeb3b on #388e3c"       # Yellow on green - line of scrimmage
STYLE_FIELD = "#388e3c"                     # Field green


class FormationDiagram(Static):
    """Renders tactical card style offensive formation diagram.

    Orientation: LOS at TOP, backfield at BOTTOM (we're looking from behind the offense).
    """

    team: reactive[Team | None] = reactive(None)
    formation: reactive[Formation | None] = reactive(None)
    personnel: reactive[PersonnelPackage | None] = reactive(None)

    # Card dimensions
    CARD_WIDTH = 43

    def render(self) -> Text:
        """Render the formation diagram as a tactical card."""
        if not self.formation or not self.team:
            return self._render_empty_state()

        text = Text()
        players = self._get_formation_players()
        diagram_lines = self._build_diagram(players)

        for i, line in enumerate(diagram_lines):
            text.append(line)
            if i < len(diagram_lines) - 1:
                text.append("\n")

        return text

    def _render_empty_state(self) -> Text:
        """Render an empty state with hatch pattern feel."""
        text = Text()
        text.append("┌" + "─" * (self.CARD_WIDTH - 2) + "┐\n", style=STYLE_BORDER)
        text.append("│" + " " * (self.CARD_WIDTH - 2) + "│\n", style=STYLE_BORDER)

        msg = "Awaiting snap..."
        padding = (self.CARD_WIDTH - 2 - len(msg)) // 2
        text.append("│", style=STYLE_BORDER)
        text.append(" " * padding + msg + " " * (self.CARD_WIDTH - 2 - padding - len(msg)), style="italic dim")
        text.append("│\n", style=STYLE_BORDER)

        text.append("│" + " " * (self.CARD_WIDTH - 2) + "│\n", style=STYLE_BORDER)
        text.append("└" + "─" * (self.CARD_WIDTH - 2) + "┘", style=STYLE_BORDER)
        return text

    def _get_formation_players(self) -> dict[str, tuple[str, int]]:
        """Get player info (jersey, overall) for each position slot."""
        if not self.team or not self.personnel:
            return {}

        players = {}
        slots = self.personnel.get_depth_slots()

        for slot in slots:
            player = self.team.get_starter(slot)
            if player:
                players[slot] = (str(player.jersey_number).zfill(2), player.overall)

        for slot in ["LT1", "LG1", "C1", "RG1", "RT1"]:
            player = self.team.get_starter(slot)
            if player:
                players[slot] = (str(player.jersey_number).zfill(2), player.overall)

        return players

    def _build_diagram(self, players: dict) -> list[Text]:
        """Build tactical card diagram for current formation."""
        if self.formation == Formation.SHOTGUN:
            return self._shotgun_card(players)
        elif self.formation == Formation.SINGLEBACK:
            return self._singleback_card(players)
        elif self.formation == Formation.I_FORM:
            return self._iform_card(players)
        elif self.formation == Formation.PISTOL:
            return self._pistol_card(players)
        elif self.formation == Formation.SPREAD:
            return self._spread_card(players)
        elif self.formation == Formation.GOAL_LINE:
            return self._goalline_card(players)
        elif self.formation == Formation.EMPTY:
            return self._empty_card(players)
        elif self.formation == Formation.UNDER_CENTER:
            return self._undercenter_card(players)
        else:
            return self._shotgun_card(players)

    # === Helper methods for building lines ===

    def _border_line(self, position: str) -> Text:
        """Build top or bottom border."""
        text = Text()
        w = self.CARD_WIDTH - 2
        if position == "top":
            text.append("┌" + "─" * w + "┐", style=STYLE_BORDER)
        else:
            text.append("└" + "─" * w + "┘", style=STYLE_BORDER)
        return text

    def _los_line(self) -> Text:
        """Line of scrimmage."""
        text = Text()
        text.append("│", style=STYLE_BORDER)
        text.append("═" * (self.CARD_WIDTH - 2), style=STYLE_LOS)
        text.append("│", style=STYLE_BORDER)
        return text

    def _empty_row(self) -> Text:
        """Build an empty row."""
        text = Text()
        text.append("│" + " " * (self.CARD_WIDTH - 2) + "│", style=STYLE_BORDER)
        return text

    # === Formation Cards (LOS at top, backfield at bottom) ===

    def _shotgun_card(self, players: dict) -> list[Text]:
        """Shotgun: QB in shotgun, spread receivers."""
        lines = []
        lines.append(self._border_line("top"))
        lines.append(self._los_line())

        # O-line with WR/TE split wide AT the line
        line = Text()
        line.append("│", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append("  ┌──┐┌──┐┌──┐┌──┐┌──┐  ", style=STYLE_OLINE_LABEL)
        line.append("TE", style=STYLE_TE)
        line.append("  ", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append("│", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│   ", style=STYLE_BORDER)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("LT", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("LG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append(" C", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RT", style=STYLE_OLINE)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("         │", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│   └──┘└──┘└──┘└──┘└──┘         │", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # QB in shotgun (centered)
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("(QB)", style=STYLE_QB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        # RB behind (centered)
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("[RB]", style=STYLE_RB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._border_line("bottom"))
        return lines

    def _singleback_card(self, players: dict) -> list[Text]:
        """Singleback: QB under center, 1 RB."""
        lines = []
        lines.append(self._border_line("top"))
        lines.append(self._los_line())

        # O-line with receivers
        line = Text()
        line.append("│", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append("  ┌──┐┌──┐┌──┐┌──┐┌──┐  ", style=STYLE_OLINE_LABEL)
        line.append("TE", style=STYLE_TE)
        line.append("  ", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append("│", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│   ", style=STYLE_BORDER)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("LT", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("LG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append(" C", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RT", style=STYLE_OLINE)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("         │", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│   └──┘└──┘└▲─┘└──┘└──┘         │", style=STYLE_BORDER)
        lines.append(line)

        # QB under center
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("(QB)", style=STYLE_QB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # RB
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("[RB]", style=STYLE_RB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._border_line("bottom"))
        return lines

    def _iform_card(self, players: dict) -> list[Text]:
        """I-Formation: QB under center, FB and RB stacked."""
        lines = []
        lines.append(self._border_line("top"))
        lines.append(self._los_line())

        # O-line
        line = Text()
        line.append("│", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append("  ┌──┐┌──┐┌──┐┌──┐┌──┐  ", style=STYLE_OLINE_LABEL)
        line.append("TE", style=STYLE_TE)
        line.append("  ", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append("│", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│   ", style=STYLE_BORDER)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("LT", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("LG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append(" C", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RT", style=STYLE_OLINE)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("         │", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│   └──┘└──┘└▲─┘└──┘└──┘         │", style=STYLE_BORDER)
        lines.append(line)

        # QB under center
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("(QB)", style=STYLE_QB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        # FB (fullback)
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("[FB]", style=STYLE_FB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        # HB (halfback)
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("[HB]", style=STYLE_RB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._border_line("bottom"))
        return lines

    def _pistol_card(self, players: dict) -> list[Text]:
        """Pistol: QB closer to line, RB directly behind."""
        lines = []
        lines.append(self._border_line("top"))
        lines.append(self._los_line())

        # O-line with slot receiver
        line = Text()
        line.append("│", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append(" ", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append(" ┌──┐┌──┐┌──┐┌──┐┌──┐ ", style=STYLE_OLINE_LABEL)
        line.append("TE", style=STYLE_TE)
        line.append("  ", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append("│", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│      ", style=STYLE_BORDER)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("LT", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("LG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append(" C", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RT", style=STYLE_OLINE)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("      │", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│      └──┘└──┘└──┘└──┘└──┘      │", style=STYLE_BORDER)
        lines.append(line)

        # QB
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("(QB)", style=STYLE_QB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        # RB directly behind
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("[RB]", style=STYLE_RB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._border_line("bottom"))
        return lines

    def _spread_card(self, players: dict) -> list[Text]:
        """Spread: 4 WR, empty look."""
        lines = []
        lines.append(self._border_line("top"))
        lines.append(self._los_line())

        # 4 WR spread wide
        line = Text()
        line.append("│", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append(" ", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append(" ┌──┐┌──┐┌──┐┌──┐┌──┐ ", style=STYLE_OLINE_LABEL)
        line.append("WR", style=STYLE_WR)
        line.append("  ", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append("│", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│      ", style=STYLE_BORDER)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("LT", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("LG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append(" C", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RT", style=STYLE_OLINE)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("      │", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│      └──┘└──┘└──┘└──┘└──┘      │", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # QB in shotgun
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("(QB)", style=STYLE_QB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        # RB
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("[RB]", style=STYLE_RB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._border_line("bottom"))
        return lines

    def _goalline_card(self, players: dict) -> list[Text]:
        """Goal line: Heavy, 2 TE, multiple backs."""
        lines = []
        lines.append(self._border_line("top"))
        lines.append(self._los_line())

        # Jumbo: TEs inline
        line = Text()
        line.append("│  ", style=STYLE_BORDER)
        line.append("TE", style=STYLE_TE)
        line.append(" ┌──┐┌──┐┌──┐┌──┐┌──┐ ", style=STYLE_OLINE_LABEL)
        line.append("TE", style=STYLE_TE)
        line.append("        │", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│     ", style=STYLE_BORDER)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("LT", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("LG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append(" C", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RT", style=STYLE_OLINE)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("        │", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│     └──┘└──┘└▲─┘└──┘└──┘        │", style=STYLE_BORDER)
        lines.append(line)

        # QB under center
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("(QB)", style=STYLE_QB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        # Two FBs
        line = Text()
        line.append("│" + " " * 13, style=STYLE_BORDER)
        line.append("[FB]", style=STYLE_FB)
        line.append("  ", style=STYLE_BORDER)
        line.append("[FB]", style=STYLE_FB)
        line.append(" " * 16 + "│", style=STYLE_BORDER)
        lines.append(line)

        # HB
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("[HB]", style=STYLE_RB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._border_line("bottom"))
        return lines

    def _empty_card(self, players: dict) -> list[Text]:
        """Empty backfield: 5 receivers, no RB."""
        lines = []
        lines.append(self._border_line("top"))
        lines.append(self._los_line())

        # 5 receivers spread
        line = Text()
        line.append("│", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append(" ", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append(" ┌──┐┌──┐┌──┐┌──┐┌──┐ ", style=STYLE_OLINE_LABEL)
        line.append("TE", style=STYLE_TE)
        line.append("  ", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append("│", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│      ", style=STYLE_BORDER)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("LT", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("LG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append(" C", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RT", style=STYLE_OLINE)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("      │", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│      └──┘└──┘└──┘└──┘└──┘      │", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # QB only (no RB in empty)
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("(QB)", style=STYLE_QB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())
        lines.append(self._border_line("bottom"))
        return lines

    def _undercenter_card(self, players: dict) -> list[Text]:
        """Under center: Traditional pro style."""
        lines = []
        lines.append(self._border_line("top"))
        lines.append(self._los_line())

        # O-line with receivers
        line = Text()
        line.append("│", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append("  ┌──┐┌──┐┌──┐┌──┐┌──┐  ", style=STYLE_OLINE_LABEL)
        line.append("TE", style=STYLE_TE)
        line.append("  ", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append("│", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│   ", style=STYLE_BORDER)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("LT", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("LG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append(" C", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RG", style=STYLE_OLINE)
        line.append("││", style=STYLE_OLINE_LABEL)
        line.append("RT", style=STYLE_OLINE)
        line.append("│", style=STYLE_OLINE_LABEL)
        line.append("         │", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│   └──┘└──┘└▲─┘└──┘└──┘         │", style=STYLE_BORDER)
        lines.append(line)

        # QB under center with slot WR
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("(QB)", style=STYLE_QB)
        line.append("  ", style=STYLE_BORDER)
        line.append("WR", style=STYLE_WR)
        line.append(" " * 13 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # RB
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("[RB]", style=STYLE_RB)
        line.append(" " * 18 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._border_line("bottom"))
        return lines

    def watch_formation(self, formation: Formation | None) -> None:
        self.refresh()

    def watch_team(self, team: Team | None) -> None:
        self.refresh()

    def watch_personnel(self, personnel: PersonnelPackage | None) -> None:
        self.refresh()


class DefensiveFormationDiagram(Static):
    """Renders tactical card style defensive formation diagram.

    Orientation: Safeties deep at TOP, D-line at LOS at BOTTOM.
    This faces the offense (which has LOS at top, backfield at bottom).
    """

    team: reactive[Team | None] = reactive(None)
    scheme: reactive[DefensiveScheme | None] = reactive(None)

    CARD_WIDTH = 43

    def render(self) -> Text:
        """Render the defensive formation."""
        if not self.scheme or not self.team:
            return self._render_empty_state()

        text = Text()
        diagram_lines = self._build_diagram()

        for i, line in enumerate(diagram_lines):
            text.append(line)
            if i < len(diagram_lines) - 1:
                text.append("\n")

        return text

    def _render_empty_state(self) -> Text:
        """Render empty defensive state."""
        text = Text()
        text.append("┌" + "─" * (self.CARD_WIDTH - 2) + "┐\n", style=STYLE_BORDER)
        text.append("│" + " " * (self.CARD_WIDTH - 2) + "│\n", style=STYLE_BORDER)
        msg = "Defense awaiting..."
        padding = (self.CARD_WIDTH - 2 - len(msg)) // 2
        text.append("│", style=STYLE_BORDER)
        text.append(" " * padding + msg + " " * (self.CARD_WIDTH - 2 - padding - len(msg)), style="italic dim")
        text.append("│\n", style=STYLE_BORDER)
        text.append("│" + " " * (self.CARD_WIDTH - 2) + "│\n", style=STYLE_BORDER)
        text.append("└" + "─" * (self.CARD_WIDTH - 2) + "┘", style=STYLE_BORDER)
        return text

    def _build_diagram(self) -> list[Text]:
        """Build diagram based on defensive scheme."""
        if self.scheme in (DefensiveScheme.COVER_0, DefensiveScheme.BLITZ_6):
            return self._blitz_card()
        elif self.scheme in (DefensiveScheme.COVER_4,):
            return self._prevent_card()
        elif self.scheme in (DefensiveScheme.COVER_2,):
            return self._cover2_card()
        else:
            return self._base43_card()

    def _border_line(self, position: str) -> Text:
        """Build border line."""
        text = Text()
        w = self.CARD_WIDTH - 2
        if position == "top":
            text.append("┌" + "─" * w + "┐", style=STYLE_BORDER)
        else:
            text.append("└" + "─" * w + "┘", style=STYLE_BORDER)
        return text

    def _los_line(self) -> Text:
        """Line of scrimmage."""
        text = Text()
        text.append("│", style=STYLE_BORDER)
        text.append("═" * (self.CARD_WIDTH - 2), style=STYLE_LOS)
        text.append("│", style=STYLE_BORDER)
        return text

    def _empty_row(self) -> Text:
        """Empty row."""
        text = Text()
        text.append("│" + " " * (self.CARD_WIDTH - 2) + "│", style=STYLE_BORDER)
        return text

    def _base43_card(self) -> list[Text]:
        """4-3 Base defense. Safeties at top, D-line at bottom."""
        lines = []
        lines.append(self._border_line("top"))

        # Safeties deep
        line = Text()
        line.append("│" + " " * 10, style=STYLE_BORDER)
        line.append("FS", style=STYLE_SAFETY)
        line.append(" " * 13, style=STYLE_BORDER)
        line.append("SS", style=STYLE_SAFETY)
        line.append(" " * 12 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # Corners and LBs
        line = Text()
        line.append("│ ", style=STYLE_BORDER)
        line.append("CB", style=STYLE_CB)
        line.append(" " * 7, style=STYLE_BORDER)
        line.append("W", style=STYLE_LB)
        line.append("   ", style=STYLE_BORDER)
        line.append("M", style=STYLE_LB)
        line.append("   ", style=STYLE_BORDER)
        line.append("S", style=STYLE_LB)
        line.append(" " * 11, style=STYLE_BORDER)
        line.append("CB", style=STYLE_CB)
        line.append(" │", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│" + " " * 10, style=STYLE_BORDER)
        line.append("(L)", style=STYLE_LB)
        line.append(" ", style=STYLE_BORDER)
        line.append("(L)", style=STYLE_LB)
        line.append(" ", style=STYLE_BORDER)
        line.append("(L)", style=STYLE_LB)
        line.append(" " * 15 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # D-Line with arrows showing rush
        line = Text()
        line.append("│" + " " * 7, style=STYLE_BORDER)
        line.append("▼", style=STYLE_DLINE_LABEL)
        line.append("  ", style=STYLE_BORDER)
        line.append("▼", style=STYLE_DLINE_LABEL)
        line.append(" " * 9, style=STYLE_BORDER)
        line.append("▼", style=STYLE_DLINE_LABEL)
        line.append("  ", style=STYLE_BORDER)
        line.append("▼", style=STYLE_DLINE_LABEL)
        line.append(" " * 13 + "│", style=STYLE_BORDER)
        lines.append(line)

        line = Text()
        line.append("│" + " " * 6, style=STYLE_BORDER)
        line.append("<E>", style=STYLE_DLINE)
        line.append(" ", style=STYLE_BORDER)
        line.append("<T>", style=STYLE_DLINE)
        line.append(" " * 7, style=STYLE_BORDER)
        line.append("<T>", style=STYLE_DLINE)
        line.append(" ", style=STYLE_BORDER)
        line.append("<E>", style=STYLE_DLINE)
        line.append(" " * 12 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._los_line())
        lines.append(self._border_line("bottom"))
        return lines

    def _cover2_card(self) -> list[Text]:
        """Cover 2 - Two deep safeties split."""
        lines = []
        lines.append(self._border_line("top"))

        # Safeties split wide
        line = Text()
        line.append("│" + " " * 5, style=STYLE_BORDER)
        line.append("FS", style=STYLE_SAFETY)
        line.append(" " * 23, style=STYLE_BORDER)
        line.append("SS", style=STYLE_SAFETY)
        line.append(" " * 7 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # Corners and LBs
        line = Text()
        line.append("│ ", style=STYLE_BORDER)
        line.append("CB", style=STYLE_CB)
        line.append(" " * 7, style=STYLE_BORDER)
        line.append("W", style=STYLE_LB)
        line.append("   ", style=STYLE_BORDER)
        line.append("M", style=STYLE_LB)
        line.append("   ", style=STYLE_BORDER)
        line.append("S", style=STYLE_LB)
        line.append(" " * 11, style=STYLE_BORDER)
        line.append("CB", style=STYLE_CB)
        line.append(" │", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # D-Line
        line = Text()
        line.append("│" + " " * 6, style=STYLE_BORDER)
        line.append("<E>", style=STYLE_DLINE)
        line.append(" ", style=STYLE_BORDER)
        line.append("<T>", style=STYLE_DLINE)
        line.append(" " * 7, style=STYLE_BORDER)
        line.append("<T>", style=STYLE_DLINE)
        line.append(" ", style=STYLE_BORDER)
        line.append("<E>", style=STYLE_DLINE)
        line.append(" " * 12 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._los_line())
        lines.append(self._border_line("bottom"))
        return lines

    def _blitz_card(self) -> list[Text]:
        """Blitz look - aggressive, LBs creeping."""
        lines = []
        lines.append(self._border_line("top"))

        # Single high safety
        line = Text()
        line.append("│" + " " * 17, style=STYLE_BORDER)
        line.append("FS", style=STYLE_SAFETY)
        line.append(" " * 20 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # Corners wide
        line = Text()
        line.append("│ ", style=STYLE_BORDER)
        line.append("CB", style=STYLE_CB)
        line.append(" " * 33, style=STYLE_BORDER)
        line.append("CB", style=STYLE_CB)
        line.append(" │", style=STYLE_BORDER)
        lines.append(line)

        # LBs creeping with arrows
        line = Text()
        line.append("│" + " " * 9, style=STYLE_BORDER)
        line.append("▼W", style=STYLE_LB)
        line.append("  ", style=STYLE_BORDER)
        line.append("▼M", style=STYLE_LB)
        line.append("  ", style=STYLE_BORDER)
        line.append("▼S", style=STYLE_LB)
        line.append(" " * 16 + "│", style=STYLE_BORDER)
        lines.append(line)

        # D-Line
        line = Text()
        line.append("│" + " " * 6, style=STYLE_BORDER)
        line.append("<E>", style=STYLE_DLINE)
        line.append(" ", style=STYLE_BORDER)
        line.append("<T>", style=STYLE_DLINE)
        line.append(" " * 7, style=STYLE_BORDER)
        line.append("<T>", style=STYLE_DLINE)
        line.append(" ", style=STYLE_BORDER)
        line.append("<E>", style=STYLE_DLINE)
        line.append(" " * 12 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._los_line())
        lines.append(self._border_line("bottom"))
        return lines

    def _prevent_card(self) -> list[Text]:
        """Prevent/Cover 4 - Lots of DBs deep."""
        lines = []
        lines.append(self._border_line("top"))

        # 4 deep
        line = Text()
        line.append("│" + " " * 3, style=STYLE_BORDER)
        line.append("CB", style=STYLE_CB)
        line.append(" " * 5, style=STYLE_BORDER)
        line.append("FS", style=STYLE_SAFETY)
        line.append(" " * 9, style=STYLE_BORDER)
        line.append("SS", style=STYLE_SAFETY)
        line.append(" " * 8, style=STYLE_BORDER)
        line.append("CB", style=STYLE_CB)
        line.append(" " * 4 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # LBs
        line = Text()
        line.append("│" + " " * 11, style=STYLE_BORDER)
        line.append("(L)", style=STYLE_LB)
        line.append(" " * 9, style=STYLE_BORDER)
        line.append("(L)", style=STYLE_LB)
        line.append(" " * 14 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._empty_row())

        # 3-man rush
        line = Text()
        line.append("│" + " " * 9, style=STYLE_BORDER)
        line.append("<E>", style=STYLE_DLINE)
        line.append(" " * 5, style=STYLE_BORDER)
        line.append("<T>", style=STYLE_DLINE)
        line.append(" " * 5, style=STYLE_BORDER)
        line.append("<E>", style=STYLE_DLINE)
        line.append(" " * 12 + "│", style=STYLE_BORDER)
        lines.append(line)

        lines.append(self._los_line())
        lines.append(self._border_line("bottom"))
        return lines

    def watch_scheme(self, scheme: DefensiveScheme | None) -> None:
        self.refresh()

    def watch_team(self, team: Team | None) -> None:
        self.refresh()


class FormationView(Vertical):
    """
    Widget displaying offensive and defensive formations as tactical cards.

    Layout: Defense on TOP (facing down), Offense on BOTTOM (facing up).
    The two lines of scrimmage meet in the middle.
    """

    DEFAULT_CSS = """
    FormationView {
        width: 46;
        height: auto;
        border: round $border;
        border-title-align: center;
        background: $surface;
        padding: 0 1;

        &:focus-within {
            border: round $accent;
        }
    }

    DefensiveFormationDiagram {
        width: 100%;
        height: auto;
    }

    FormationDiagram {
        width: 100%;
        height: auto;
    }

    .formation-label {
        text-align: center;
        color: #666666;
        text-style: bold;
        margin-bottom: 0;
    }
    """

    # Offense data
    offense_team: reactive[Team | None] = reactive(None)
    formation: reactive[Formation | None] = reactive(None)
    personnel: reactive[PersonnelPackage | None] = reactive(None)

    # Defense data
    defense_team: reactive[Team | None] = reactive(None)
    defensive_scheme: reactive[DefensiveScheme | None] = reactive(None)

    def compose(self) -> ComposeResult:
        """Compose the formation view: Defense on top, Offense on bottom."""
        yield Static("DEFENSE", classes="formation-label", id="defense-label")
        yield DefensiveFormationDiagram(id="defensive-diagram")
        yield Static("OFFENSE", classes="formation-label", id="offense-label")
        yield FormationDiagram(id="formation-diagram")

    def on_mount(self) -> None:
        """Set up the view."""
        self._update_title()

    def _update_title(self) -> None:
        """Update border title with formation info."""
        parts = []
        if self.formation and self.offense_team:
            parts.append(f"{self.offense_team.abbreviation} {self.formation.value}")
            if self.personnel:
                parts.append(f"[{self.personnel.value}]")

        if self.defensive_scheme and self.defense_team:
            scheme_name = self.defensive_scheme.name.replace("_", " ").title()
            parts.append(f"vs {scheme_name}")

        self.border_title = " ".join(parts) if parts else "Formations"

    def update_from_play(
        self,
        offense_team: Team,
        defense_team: Team,
        formation: Optional[Formation],
        personnel: Optional[PersonnelPackage],
        defensive_scheme: Optional[DefensiveScheme],
    ) -> None:
        """Update both formations from play data."""
        self.offense_team = offense_team
        self.defense_team = defense_team
        self.formation = formation
        self.personnel = personnel
        self.defensive_scheme = defensive_scheme

        try:
            offense_diag = self.query_one("#formation-diagram", FormationDiagram)
            offense_diag.team = offense_team
            offense_diag.formation = formation
            offense_diag.personnel = personnel
        except Exception:
            pass

        try:
            defense_diag = self.query_one("#defensive-diagram", DefensiveFormationDiagram)
            defense_diag.team = defense_team
            defense_diag.scheme = defensive_scheme
        except Exception:
            pass

        self._update_title()

    def update_from_play_call(
        self,
        team: Team,
        formation: Optional[Formation],
        personnel: Optional[PersonnelPackage],
    ) -> None:
        """Update display from a play call (backwards compat)."""
        self.offense_team = team
        self.formation = formation
        self.personnel = personnel

        try:
            diagram = self.query_one("#formation-diagram", FormationDiagram)
            diagram.team = team
            diagram.formation = formation
            diagram.personnel = personnel
        except Exception:
            pass

        self._update_title()

    def clear(self) -> None:
        """Clear the formation display."""
        self.offense_team = None
        self.defense_team = None
        self.formation = None
        self.personnel = None
        self.defensive_scheme = None
        self._update_title()

    def watch_formation(self, formation: Formation | None) -> None:
        self._update_title()

    def watch_offensive_scheme(self, scheme: DefensiveScheme | None) -> None:
        self._update_title()
