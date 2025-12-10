"""
Position-specific philosophy enums.

Each position has multiple philosophies that a team can adopt.
These philosophies change which attributes are emphasized when
calculating a player's OVR for that team.

Based on NFL Head Coach 09's philosophy system.
"""

from enum import Enum


class QBPhilosophy(Enum):
    """
    Quarterback evaluation philosophies.

    STRONG_ARM: Big arm, physical tools - THP, STR, ELU
    PURE_PASSER: Accuracy-focused pocket passer - THP, TAS/TAM/TAD, AWR
    FIELD_GENERAL: Smart, experienced leader - LRN, AWR, TAS/TAM
    MOBILE: Dual-threat scrambler - SPD, ACC, AGI, ELU
    """
    STRONG_ARM = "strong_arm"
    PURE_PASSER = "pure_passer"
    FIELD_GENERAL = "field_general"
    MOBILE = "mobile"


class RBPhilosophy(Enum):
    """
    Running back evaluation philosophies.

    POWER: Downhill runner - TRK, SFA, BTK, STR
    RECEIVING: Pass-catching back - CTH, AWR, CAR, CIT, RTE
    MOVES: Elusive runner - JKM, SPN, ELU
    SPEED: Home-run threat - SPD, ACC, AGI
    WORKHORSE: Bell-cow back - STA, TGH, INJ, STR
    """
    POWER = "power"
    RECEIVING = "receiving"
    MOVES = "moves"
    SPEED = "speed"
    WORKHORSE = "workhorse"


class WRPhilosophy(Enum):
    """
    Wide receiver evaluation philosophies.

    STRONG: Physical possession receiver - STR, CIT, CTH, BTK
    TALL: Red zone threat, contested catches - JMP, SPC, CIT
    QUICK: Route technician - RTE, REL, AGI
    SPEED: Deep threat - SPD, ACC, SPC
    """
    STRONG = "strong"
    TALL = "tall"
    QUICK = "quick"
    SPEED = "speed"


class TEPhilosophy(Enum):
    """
    Tight end evaluation philosophies.

    SOFT_HANDS: Receiving-focused - CTH, CIT, RTE
    PLAYMAKER: Move TE / big slot - SPD, AGI, CTH, RTE
    BLOCKER: Traditional Y-TE - RBK, PBK, STR
    """
    SOFT_HANDS = "soft_hands"
    PLAYMAKER = "playmaker"
    BLOCKER = "blocker"


class OLPhilosophy(Enum):
    """
    Offensive line evaluation philosophies.

    ZONE_BLOCKING: Outside zone scheme - AGI, SPD, RBK, AWR
    RUN_BLOCK: Power scheme - STR, RBK, IMP
    PASS_BLOCK: Pass-first offense - PBK, AWR, STR
    """
    ZONE_BLOCKING = "zone_blocking"
    RUN_BLOCK = "run_block"
    PASS_BLOCK = "pass_block"


class DLPhilosophy(Enum):
    """
    Defensive line evaluation philosophies.

    ONE_GAP: Penetrating speed rusher - FNM, SPD, ACC, BSH
    RUN_STOPPER: Two-gap anchor - STR, BSH, TAK
    VERSATILE: 3-4 hybrid - PWM, FNM, BSH, STR
    """
    ONE_GAP = "one_gap"
    RUN_STOPPER = "run_stopper"
    VERSATILE = "versatile"


class LBPhilosophy(Enum):
    """
    Linebacker evaluation philosophies.

    COVERAGE: Modern LB who can cover - ZON, MAN, SPD, AWR
    RUN_STOPPER: Thumper against the run - TAK, BSH, STR, POW
    BLITZER: Pass rush specialist - PUR, SPD, FNM, POW
    """
    COVERAGE = "coverage"
    RUN_STOPPER = "run_stopper"
    BLITZER = "blitzer"


class CBPhilosophy(Enum):
    """
    Cornerback evaluation philosophies.

    COVER_2: Zone corner with range - ZON, SPD, PRC, AWR
    MAN_COVERAGE: Sticky man-to-man - MAN, SPD, AGI, PRS
    PRESS_RUN_SUPPORT: Physical corner - PRS, TAK, STR, POW
    """
    COVER_2 = "cover_2"
    MAN_COVERAGE = "man_coverage"
    PRESS_RUN_SUPPORT = "press_run_support"


class FSPhilosophy(Enum):
    """
    Free safety evaluation philosophies.

    CENTERFIELDER: Deep coverage ballhawk - ZON, SPD, PRC, AWR
    MAN_COVERAGE: Slot coverage specialist - MAN, SPD, AGI
    RUN_STOPPER: Box safety who hits - TAK, POW, STR, PUR
    """
    CENTERFIELDER = "centerfielder"
    MAN_COVERAGE = "man_coverage"
    RUN_STOPPER = "run_stopper"


class SSPhilosophy(Enum):
    """
    Strong safety evaluation philosophies.

    COVERAGE: Modern safety in coverage - ZON, MAN, SPD, AWR
    SMART_PRODUCTIVE: All-around playmaker - AWR, PRC, TAK, ZON
    BIG_HITTER: Enforcer - POW, TAK, STR, PUR
    """
    COVERAGE = "coverage"
    SMART_PRODUCTIVE = "smart_productive"
    BIG_HITTER = "big_hitter"
