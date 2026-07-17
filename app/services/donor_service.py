"""Donor service helpers."""


def get_top_donors(blood_group: str, city: str):
    return {
        "blood_group": blood_group,
        "city": city,
        "donors": [],
    }
