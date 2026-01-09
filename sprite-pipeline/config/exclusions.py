"""
Exclusion rules for hair/beard combinations that don't work well.
"""

# Hair styles banned for ALL face widths
# Format: (row, col)
HAIR_BANNED_ALL = [
    (6, 7),
]

# Hair styles banned for specific face batches
# Format: {batch_name: [(row, col), ...]}
HAIR_BANNED_BY_BATCH = {
    "batch1": [
        (2, 2),
    ],
    "batch2": [
        (2, 2),
    ],
}

# Hair styles banned for specific face widths
# Format: {face_width: [(row, col), ...]}
HAIR_BANNED_BY_WIDTH = {
    7: [  # Widest face
        (4, 4),
        (4, 5),
        (4, 6),
        (4, 7),
        (5, 1),
        (5, 6),
        (6, 7),  # Also in BANNED_ALL, but explicit here
    ],
}

# Facial hair styles banned for ALL face widths
FACIAL_BANNED_ALL = [
    (1, 1),  # Doesn't fit well
]

# Facial hair styles banned for specific face widths
FACIAL_BANNED_BY_WIDTH = {}


def is_hair_allowed(hair_row: int, hair_col: int, face_width: int, face_batch: str = None) -> bool:
    """Check if a hair style is allowed for a given face width and batch."""
    hair = (hair_row, hair_col)

    # Check global ban
    if hair in HAIR_BANNED_ALL:
        return False

    # Check width-specific ban
    if face_width in HAIR_BANNED_BY_WIDTH:
        if hair in HAIR_BANNED_BY_WIDTH[face_width]:
            return False

    # Check batch-specific ban
    if face_batch and face_batch in HAIR_BANNED_BY_BATCH:
        if hair in HAIR_BANNED_BY_BATCH[face_batch]:
            return False

    return True


def is_facial_allowed(facial_row: int, facial_col: int, face_width: int) -> bool:
    """Check if a facial hair style is allowed for a given face width."""
    facial = (facial_row, facial_col)

    # Check global ban
    if facial in FACIAL_BANNED_ALL:
        return False

    # Check width-specific ban
    if face_width in FACIAL_BANNED_BY_WIDTH:
        if facial in FACIAL_BANNED_BY_WIDTH[face_width]:
            return False

    return True
