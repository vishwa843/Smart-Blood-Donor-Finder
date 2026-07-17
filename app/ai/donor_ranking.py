"""Donor ranking helpers."""


def rank_donors(donors: list[dict]) -> list[dict]:
    return sorted(donors, key=lambda donor: donor.get("score", 0), reverse=True)
