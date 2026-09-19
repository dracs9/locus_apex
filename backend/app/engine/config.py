"""All thresholds and weights of the scoring engine. Documented in README."""

# Kazakh 5-point GPA -> US 4-point GPA (approximate, linear between points)
GPA5_TO_GPA4 = [(2.0, 1.0), (3.0, 2.0), (3.5, 2.5), (4.0, 3.0), (4.5, 3.5), (5.0, 4.0)]

# Tier rules (§8.5)
DREAM_ACCEPTANCE_BELOW = 0.15
SAFETY_ACCEPTANCE_FROM = 0.30
GPA_WITHIN_MARGIN = 0.2

# A "below" gap counts as closable before the deadline if it is not larger than this
# and there are at least MIN_DAYS_TO_CLOSE_GAP days left.
SAT_CLOSABLE_GAP = 150
GPA4_CLOSABLE_GAP = 0.3
MIN_DAYS_TO_CLOSE_GAP = 60

# Score weights (sum = 1.0). Each factor is in 0..1, final score is 0..100.
WEIGHTS = {
    "academic": 0.35,
    "language": 0.15,
    "major": 0.10,
    "affordability": 0.20,
    "priorities": 0.15,
    "achievements": 0.05,
}

# Academic sub-factor values
FIT_VALUE = {"above": 1.0, "within": 0.7, "below": 0.3, "missing": 0.4}
LANGUAGE_VALUE = {"ok": 1.0, "missing": 0.5, "below_planned": 0.3}
UNKNOWN_FACTOR = 0.5

# Achievement bonus by level (sum capped at 1.0)
LEVEL_BONUS = {"school": 0.1, "city": 0.2, "national": 0.5, "international": 1.0}
ACTIVITY_TYPES = ("OLYMPIAD", "PROJECT", "VOLUNTEER", "COMPETITION", "OTHER")

# Prestige: world_rank 1 -> 1.0, PRESTIGE_RANK_FLOOR and below -> 0.0, on a log scale
# so that #27 and #89 differ noticeably (a linear scale made the top 100 almost equal).
PRESTIGE_RANK_FLOOR = 600
# Cost priority: cheaper is better, $0 -> 1.0, PRIORITY_COST_CEILING and above -> 0.0.
# The budget itself is handled by the affordability factor.
PRIORITY_COST_CEILING = 100_000
AID_VALUE = {"full_need": 1.0, "partial": 0.6, "merit_only": 0.3, "none": 0.0}

# ETS TOEFL iBT -> IELTS comparison (lower bound of TOEFL band, IELTS band)
TOEFL_TO_IELTS = [(118, 9.0), (115, 8.5), (110, 8.0), (102, 7.5), (94, 7.0), (79, 6.5),
                  (60, 6.0), (46, 5.5), (35, 5.0), (32, 4.5), (0, 4.0)]

# Roadmap
BLOCKER_CODES = ("MAJOR_NOT_OFFERED", "OVER_BUDGET", "REQUIREMENT_UNREACHABLE", "IELTS_BELOW_MIN")
GAP_CODES = ("SAT_BELOW_P25", "SAT_MISSING", "GPA_BELOW_AVG", "IELTS_MISSING", "IELTS_BELOW_MIN",
             "OVER_BUDGET", "REQUIREMENT_UNREACHABLE", "OVER_BUDGET_NEEDS_AID")
TOP_RECS_FOR_ROADMAP = 3
MAX_SUGGESTIONS = 4
