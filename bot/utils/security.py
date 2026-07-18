"""
Security-sensitive helpers: referral code generation and the
cryptographically secure RNG used for winner selection.
"""

import secrets
import string

_CODE_ALPHABET = string.ascii_lowercase + string.digits
_CODE_LENGTH = 8


def generate_referral_code() -> str:
    """
    Generates a short, non-guessable referral code. Deliberately pure
    randomness, not derived from a user_id — an id-derived code would
    let anyone attribute fake conversions to a specific victim
    referrer. Caller (ReferralService) is responsible for retrying on
    the rare collision against the UNIQUE constraint on users.referral_code.
    """
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


def secure_choice_weighted(candidates: list, weights: list[int], count: int) -> list:
    """
    Draws `count` unique winners from `candidates`, weighted by
    `weights` (ticket counts), using secrets.SystemRandom (a CSPRNG)
    rather than the stdlib `random` module — required for fair,
    non-predictable giveaway winner selection.

    Each draw is weighted over whatever remains in the pool, then that
    candidate is removed — so higher ticket counts improve someone's
    odds without letting them win more than one position.
    """
    if len(candidates) != len(weights):
        raise ValueError("candidates and weights must be the same length")
    if count < 0:
        raise ValueError("count must be non-negative")
    if count > len(candidates):
        raise ValueError("count cannot exceed the number of candidates")

    rng = secrets.SystemRandom()
    pool = list(zip(candidates, weights))
    chosen = []
    for _ in range(count):
        total_weight = sum(weight for _, weight in pool)
        pick = rng.uniform(0, total_weight)
        cumulative = 0
        for index, (candidate, weight) in enumerate(pool):
            cumulative += weight
            if pick <= cumulative:
                chosen.append(candidate)
                pool.pop(index)
                break
    return chosen
