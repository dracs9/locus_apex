"""Chance history (§8.8): re-run the engine on the profile as it was on each achievement date."""
from app.schemas import ChancePoint, Profile, University

from .normalize import profile_at
from .recommend import recommend


def chance_history(profile: Profile, university_ids: list[str], universities: list[University],
                   major_names: dict[str, str] | None = None) -> list[ChancePoint]:
    points: dict = {profile.created_at.date(): None}
    for a in sorted(profile.achievements, key=lambda a: (a.date, str(a.id))):
        if a.status == "done":
            points.setdefault(a.date, str(a.id))
            if points[a.date] is None:
                points[a.date] = str(a.id)

    out = []
    for at in sorted(points):
        result = recommend(profile_at(profile, at), universities, at, major_names)
        chances = {r.university_id: r.chance for r in result.recs}
        out.append(ChancePoint(date=at, chance_by_uni={uid: chances.get(uid) for uid in university_ids},
                               achievement_id=points[at]))
    return out
