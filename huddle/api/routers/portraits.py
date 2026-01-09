"""Portraits API router - player portrait generation and retrieval."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Paths
# portraits.py is at huddle/huddle/api/routers/portraits.py
# Project root is 4 parents up: routers -> api -> huddle -> huddle (package) -> huddle (project)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SPRITE_PIPELINE_PATH = PROJECT_ROOT / "sprite-pipeline"
HUDDLE_DATA_PATH = PROJECT_ROOT / "data"

router = APIRouter(prefix="/portraits", tags=["portraits"])

# Lazy-loaded generator
_generator = None


def get_generator():
    """Get or create the portrait generator (lazy import)."""
    global _generator
    if _generator is None:
        # Add sprite-pipeline to path and import
        if str(SPRITE_PIPELINE_PATH) not in sys.path:
            sys.path.insert(0, str(SPRITE_PIPELINE_PATH))
        from generator import PortraitGenerator
        _generator = PortraitGenerator(SPRITE_PIPELINE_PATH)
    return _generator


def get_portrait_config(**kwargs):
    """Create a PortraitConfig (lazy import)."""
    if str(SPRITE_PIPELINE_PATH) not in sys.path:
        sys.path.insert(0, str(SPRITE_PIPELINE_PATH))
    from generator import PortraitConfig
    return PortraitConfig(**kwargs)


def get_league_portraits_dir(league_id: str) -> Path:
    """Get the portraits directory for a league."""
    return HUDDLE_DATA_PATH / "leagues" / league_id / "portraits"


def get_portrait_path(league_id: str, player_id: str) -> Path:
    """Get the full path for a player's portrait."""
    return get_league_portraits_dir(league_id) / f"{player_id}.png"


# Pydantic schemas
class PortraitGenerateRequest(BaseModel):
    """Request to generate a portrait."""
    league_id: str
    player_id: str
    position: Optional[str] = None
    age: Optional[int] = None
    skin_tone: Optional[int] = None  # 0-7
    face_width: Optional[int] = None  # 0-7
    hair_style: Optional[list[int]] = None  # [row, col]
    hair_color: Optional[str] = None
    facial_style: Optional[list[int]] = None  # [row, col]
    facial_color: Optional[str] = None
    no_hair: bool = False
    no_facial_hair: bool = False
    seed: Optional[int] = None


class PortraitAttributes(BaseModel):
    """Generated portrait attributes."""
    skin_tone: int
    face_width: int
    hair_style: Optional[list[int]] = None
    hair_style_name: Optional[str] = None
    hair_color: Optional[str] = None
    facial_style: Optional[list[int]] = None
    facial_style_name: Optional[str] = None
    facial_color: Optional[str] = None


class PortraitGenerateResponse(BaseModel):
    """Response from portrait generation."""
    league_id: str
    player_id: str
    portrait_url: str
    status: str  # pending | generating | ready | failed
    attributes: PortraitAttributes


class PortraitStatusResponse(BaseModel):
    """Portrait status response."""
    league_id: str
    player_id: str
    status: str
    portrait_url: Optional[str] = None


class PortraitDescriptionRequest(BaseModel):
    """Request for a player appearance description."""
    skin_tone: int
    face_width: int
    hair_style: Optional[list[int]] = None
    hair_color: Optional[str] = None
    facial_style: Optional[list[int]] = None
    facial_color: Optional[str] = None


class PortraitDescriptionResponse(BaseModel):
    """Response with player appearance description."""
    description: str


class StyleOption(BaseModel):
    """A style option."""
    id: list[int]
    name: Optional[str] = None
    description: Optional[str] = None


class PortraitOptionsResponse(BaseModel):
    """Available portrait options."""
    skin_tones: list[int]
    face_widths: list[int]
    hair_colors: list[str]
    hair_styles: list[StyleOption]
    facial_styles: list[StyleOption]


class BatchPlayerInput(BaseModel):
    """Player info for batch portrait generation."""
    player_id: str
    position: Optional[str] = None
    age: Optional[int] = None
    weight_lbs: Optional[int] = None  # For face_width restrictions
    priority: int = 0  # Higher = generated first (for user team prioritization)


class BatchGenerateRequest(BaseModel):
    """Request to generate portraits for multiple players."""
    league_id: str
    players: list[BatchPlayerInput]


class BatchGenerateResponse(BaseModel):
    """Response from batch portrait generation request."""
    league_id: str
    queued_count: int
    status: str  # "queued" | "processing" | "complete"
    message: str


class BatchStatusResponse(BaseModel):
    """Status of batch portrait generation."""
    league_id: str
    total: int
    completed: int
    failed: int
    pending: int
    status: str  # "processing" | "complete"


# In-memory status tracking (will be replaced by DB)
_portrait_status: dict[str, dict] = {}

# Batch generation tracking
_batch_status: dict[str, dict] = {}  # league_id -> {total, completed, failed, pending}


def _generate_portrait_sync(
    league_id: str,
    player_id: str,
    position: Optional[str] = None,
    age: Optional[int] = None,
) -> bool:
    """
    Synchronously generate a single portrait.
    Returns True on success, False on failure.
    """
    try:
        generator = get_generator()
        config = get_portrait_config(
            player_id=player_id,
            position=position,
            age=age,
        )

        # Generate portrait
        portrait_image = generator.generate(config)

        # Save to league directory
        portraits_dir = get_league_portraits_dir(league_id)
        portraits_dir.mkdir(parents=True, exist_ok=True)
        output_path = get_portrait_path(league_id, player_id)
        portrait_image.save(output_path, "PNG")

        # Store status
        attrs = config.generated_attributes
        status_key = f"{league_id}/{player_id}"
        _portrait_status[status_key] = {
            "status": "ready",
            "path": str(output_path),
            "attributes": attrs,
        }
        return True

    except Exception as e:
        print(f"[PORTRAITS] ERROR generating {player_id}: {e}")
        status_key = f"{league_id}/{player_id}"
        _portrait_status[status_key] = {
            "status": "failed",
            "error": str(e),
        }
        return False


def _process_batch_portraits(league_id: str, players: list[BatchPlayerInput]) -> None:
    """
    Background task to generate portraits for multiple players.
    Players are sorted by priority (higher first) to prioritize user's team.
    """
    print(f"[PORTRAITS] Starting batch generation for {len(players)} players in league {league_id}")

    # Initialize batch status (may already be set by management.py for immediate visibility)
    _batch_status[league_id] = {
        "total": len(players),
        "completed": 0,
        "failed": 0,
        "pending": len(players),
    }

    # Sort by priority (descending - higher priority first)
    sorted_players = sorted(players, key=lambda p: p.priority, reverse=True)

    for i, player in enumerate(sorted_players):
        success = _generate_portrait_sync(
            league_id=league_id,
            player_id=player.player_id,
            position=player.position,
            age=player.age,
        )

        if success:
            _batch_status[league_id]["completed"] += 1
        else:
            _batch_status[league_id]["failed"] += 1

        _batch_status[league_id]["pending"] -= 1

        # Log progress every 50 portraits
        if (i + 1) % 50 == 0 or i == 0:
            completed = _batch_status[league_id]["completed"]
            failed = _batch_status[league_id]["failed"]
            print(f"[PORTRAITS] Progress: {i + 1}/{len(players)} (success: {completed}, failed: {failed})")

    print(f"[PORTRAITS] Batch complete: {_batch_status[league_id]['completed']} success, {_batch_status[league_id]['failed']} failed")


@router.post("/generate", response_model=PortraitGenerateResponse)
async def generate_portrait(request: PortraitGenerateRequest) -> PortraitGenerateResponse:
    """
    Generate a portrait for a player.

    If attributes are not specified, they will be randomly selected
    based on position demographics and age.
    """
    generator = get_generator()

    # Build config
    config = get_portrait_config(
        player_id=request.player_id,
        position=request.position,
        age=request.age,
        skin_tone=request.skin_tone,
        face_width=request.face_width,
        hair_style=tuple(request.hair_style) if request.hair_style else None,
        hair_color=request.hair_color,
        facial_style=tuple(request.facial_style) if request.facial_style else None,
        facial_color=request.facial_color,
        no_hair=request.no_hair,
        no_facial_hair=request.no_facial_hair,
        seed=request.seed,
    )

    try:
        # Generate portrait
        portrait_image = generator.generate(config)

        # Save to league directory
        portraits_dir = get_league_portraits_dir(request.league_id)
        portraits_dir.mkdir(parents=True, exist_ok=True)
        output_path = get_portrait_path(request.league_id, request.player_id)
        portrait_image.save(output_path, "PNG")

        # Store status
        attrs = config.generated_attributes
        status_key = f"{request.league_id}/{request.player_id}"
        _portrait_status[status_key] = {
            "status": "ready",
            "path": str(output_path),
            "attributes": attrs,
        }

        return PortraitGenerateResponse(
            league_id=request.league_id,
            player_id=request.player_id,
            portrait_url=f"/api/v1/portraits/{request.league_id}/{request.player_id}",
            status="ready",
            attributes=PortraitAttributes(
                skin_tone=attrs["skin_tone"],
                face_width=attrs["face_width"],
                hair_style=list(attrs["hair_style"]) if attrs["hair_style"] else None,
                hair_style_name=attrs["hair_style_name"],
                hair_color=attrs["hair_color"],
                facial_style=list(attrs["facial_style"]) if attrs["facial_style"] else None,
                facial_style_name=attrs["facial_style_name"],
                facial_color=attrs["facial_color"],
            ),
        )
    except Exception as e:
        status_key = f"{request.league_id}/{request.player_id}"
        _portrait_status[status_key] = {
            "status": "failed",
            "error": str(e),
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portrait generation failed: {e}",
        )


@router.get("/options", response_model=PortraitOptionsResponse)
async def get_portrait_options() -> PortraitOptionsResponse:
    """Get all available options for portrait generation."""
    generator = get_generator()
    options = generator.get_available_options()

    return PortraitOptionsResponse(
        skin_tones=options["skin_tones"],
        face_widths=options["face_widths"],
        hair_colors=options["hair_colors"],
        hair_styles=[StyleOption(**s) for s in options["hair_styles"]],
        facial_styles=[StyleOption(**s) for s in options["facial_styles"]],
    )


@router.post("/describe", response_model=PortraitDescriptionResponse)
async def get_player_description(request: PortraitDescriptionRequest) -> PortraitDescriptionResponse:
    """
    Get a human-readable description of a player's appearance.

    Use this to generate text descriptions for players based on their
    portrait attributes. Useful for accessibility, scout reports, or
    narrative content.
    """
    generator = get_generator()

    description = generator.get_player_description(
        skin_tone=request.skin_tone,
        face_width=request.face_width,
        hair_style=tuple(request.hair_style) if request.hair_style else None,
        hair_color=request.hair_color,
        facial_style=tuple(request.facial_style) if request.facial_style else None,
        facial_color=request.facial_color,
    )

    return PortraitDescriptionResponse(description=description)


@router.get("/status/{league_id}/{player_id}", response_model=PortraitStatusResponse)
async def get_portrait_status(league_id: str, player_id: str) -> PortraitStatusResponse:
    """Check the generation status of a portrait."""
    status_key = f"{league_id}/{player_id}"
    status_info = _portrait_status.get(status_key)

    if status_info is None:
        # Check if file exists on disk
        portrait_path = get_portrait_path(league_id, player_id)
        if portrait_path.exists():
            return PortraitStatusResponse(
                league_id=league_id,
                player_id=player_id,
                status="ready",
                portrait_url=f"/api/v1/portraits/{league_id}/{player_id}",
            )
        return PortraitStatusResponse(
            league_id=league_id,
            player_id=player_id,
            status="pending",
            portrait_url=None,
        )

    return PortraitStatusResponse(
        league_id=league_id,
        player_id=player_id,
        status=status_info["status"],
        portrait_url=f"/api/v1/portraits/{league_id}/{player_id}" if status_info["status"] == "ready" else None,
    )


@router.get("/{league_id}/{player_id}/attributes", response_model=PortraitAttributes)
async def get_portrait_attributes(league_id: str, player_id: str) -> PortraitAttributes:
    """
    Get a player's portrait attributes (facial hair, hair style, etc.).

    Useful for debugging and inspection.
    """
    status_key = f"{league_id}/{player_id}"
    status_info = _portrait_status.get(status_key)

    if status_info is None or "attributes" not in status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait attributes not found (portrait may need regeneration)",
        )

    attrs = status_info["attributes"]
    return PortraitAttributes(
        skin_tone=attrs["skin_tone"],
        face_width=attrs["face_width"],
        hair_style=list(attrs["hair_style"]) if attrs.get("hair_style") else None,
        hair_style_name=attrs.get("hair_style_name"),
        hair_color=attrs.get("hair_color"),
        facial_style=list(attrs["facial_style"]) if attrs.get("facial_style") else None,
        facial_style_name=attrs.get("facial_style_name"),
        facial_color=attrs.get("facial_color"),
    )


@router.get("/{league_id}/{player_id}")
async def get_portrait(league_id: str, player_id: str) -> FileResponse:
    """
    Get a player's portrait image.

    Returns the generated portrait if available, otherwise returns a placeholder.
    """
    # Check if portrait exists
    portrait_path = get_portrait_path(league_id, player_id)

    if portrait_path.exists():
        return FileResponse(
            path=str(portrait_path),
            media_type="image/png",
            filename=f"{player_id}.png",
        )

    # Return placeholder
    placeholder_path = SPRITE_PIPELINE_PATH / "output" / "portraits" / "placeholder.png"

    if not placeholder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portrait not found and no placeholder available",
        )

    return FileResponse(
        path=str(placeholder_path),
        media_type="image/png",
        filename="placeholder.png",
    )


@router.post("/regenerate/{league_id}/{player_id}", response_model=PortraitGenerateResponse)
async def regenerate_portrait(
    league_id: str,
    player_id: str,
    position: Optional[str] = None,
    age: Optional[int] = None,
) -> PortraitGenerateResponse:
    """
    Regenerate a player's portrait.

    Useful for:
    - Aging updates (gray hair)
    - Draft transition (prospect → rostered)
    - Style changes

    If position/age provided, uses those; otherwise uses previously stored attributes.
    """
    generator = get_generator()

    # Get previous attributes if available
    status_key = f"{league_id}/{player_id}"
    prev_status = _portrait_status.get(status_key, {})
    prev_attrs = prev_status.get("attributes", {})

    # Build config - keep skin_tone and face_width, regenerate hair
    config = get_portrait_config(
        player_id=player_id,
        position=position,
        age=age,
        skin_tone=prev_attrs.get("skin_tone"),
        face_width=prev_attrs.get("face_width"),
        # Let hair be re-rolled based on new age
    )

    try:
        # Generate portrait
        portrait_image = generator.generate(config)

        # Save to league directory
        portraits_dir = get_league_portraits_dir(league_id)
        portraits_dir.mkdir(parents=True, exist_ok=True)
        output_path = get_portrait_path(league_id, player_id)
        portrait_image.save(output_path, "PNG")

        attrs = config.generated_attributes
        _portrait_status[status_key] = {
            "status": "ready",
            "path": str(output_path),
            "attributes": attrs,
        }

        return PortraitGenerateResponse(
            league_id=league_id,
            player_id=player_id,
            portrait_url=f"/api/v1/portraits/{league_id}/{player_id}",
            status="ready",
            attributes=PortraitAttributes(
                skin_tone=attrs["skin_tone"],
                face_width=attrs["face_width"],
                hair_style=list(attrs["hair_style"]) if attrs["hair_style"] else None,
                hair_style_name=attrs["hair_style_name"],
                hair_color=attrs["hair_color"],
                facial_style=list(attrs["facial_style"]) if attrs["facial_style"] else None,
                facial_style_name=attrs["facial_style_name"],
                facial_color=attrs["facial_color"],
            ),
        )
    except Exception as e:
        _portrait_status[status_key] = {
            "status": "failed",
            "error": str(e),
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portrait regeneration failed: {e}",
        )


@router.delete("/{league_id}/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portrait(league_id: str, player_id: str) -> None:
    """Delete a player's portrait."""
    portrait_path = get_portrait_path(league_id, player_id)

    if portrait_path.exists():
        portrait_path.unlink()

    status_key = f"{league_id}/{player_id}"
    if status_key in _portrait_status:
        del _portrait_status[status_key]


@router.delete("/{league_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_league_portraits(league_id: str) -> None:
    """Delete all portraits for a league."""
    import shutil

    portraits_dir = get_league_portraits_dir(league_id)

    if portraits_dir.exists():
        shutil.rmtree(portraits_dir)

    # Clean up status entries for this league
    keys_to_delete = [k for k in _portrait_status if k.startswith(f"{league_id}/")]
    for key in keys_to_delete:
        del _portrait_status[key]

    # Clean up batch status
    if league_id in _batch_status:
        del _batch_status[league_id]


@router.post("/batch/generate", response_model=BatchGenerateResponse)
async def batch_generate_portraits(
    request: BatchGenerateRequest,
    background_tasks: BackgroundTasks,
) -> BatchGenerateResponse:
    """
    Queue portrait generation for multiple players.

    This runs in the background and returns immediately.
    Use GET /batch/status/{league_id} to check progress.

    Priority field on players determines generation order:
    - Higher priority = generated first
    - Use priority=100 for user's team to prioritize them
    """
    if not request.players:
        return BatchGenerateResponse(
            league_id=request.league_id,
            queued_count=0,
            status="complete",
            message="No players to generate portraits for",
        )

    # Initialize batch status as processing
    _batch_status[request.league_id] = {
        "total": len(request.players),
        "completed": 0,
        "failed": 0,
        "pending": len(request.players),
    }

    # Add to background tasks
    background_tasks.add_task(
        _process_batch_portraits,
        request.league_id,
        request.players,
    )

    return BatchGenerateResponse(
        league_id=request.league_id,
        queued_count=len(request.players),
        status="processing",
        message=f"Queued {len(request.players)} portraits for generation",
    )


@router.get("/batch/status/{league_id}", response_model=BatchStatusResponse)
async def get_batch_status(league_id: str) -> BatchStatusResponse:
    """
    Get the status of batch portrait generation for a league.
    """
    batch_info = _batch_status.get(league_id)

    if batch_info is None:
        # No batch in progress - check if portraits exist
        portraits_dir = get_league_portraits_dir(league_id)
        if portraits_dir.exists():
            count = len(list(portraits_dir.glob("*.png")))
            return BatchStatusResponse(
                league_id=league_id,
                total=count,
                completed=count,
                failed=0,
                pending=0,
                status="complete",
            )
        return BatchStatusResponse(
            league_id=league_id,
            total=0,
            completed=0,
            failed=0,
            pending=0,
            status="complete",
        )

    is_complete = batch_info["pending"] == 0
    return BatchStatusResponse(
        league_id=league_id,
        total=batch_info["total"],
        completed=batch_info["completed"],
        failed=batch_info["failed"],
        pending=batch_info["pending"],
        status="complete" if is_complete else "processing",
    )
