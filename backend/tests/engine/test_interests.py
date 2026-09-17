import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.profile import AcademicRecord, HollandAssessment
from app.engine.interests import questionnaire, scores, interest_fit
from app.engine.normalize import profile_gpa4
from .conftest import make_profile, make_uni


def answers(value=2):
    return {q['id']: value for q in questionnaire()['questions']}


def test_questionnaire_frontend_parity():
    root = Path(__file__).parents[3]
    assert questionnaire() == json.loads((root / 'frontend/src/data/holland.json').read_text())


@pytest.mark.parametrize('scale,value', [('ib8', 8.1), ('4', 4.1), ('100', 101), ('5', -1)])
def test_academic_range(scale, value):
    with pytest.raises(ValidationError):
        AcademicRecord(scale=scale, value=value)


def test_no_invented_ib_conversion():
    p = make_profile(grade=9, academic_record={'scale': 'ib8', 'value': 8})
    assert profile_gpa4(p) is None
    assert profile_gpa4(make_profile(academic_record={'scale': '4', 'value': 0})) == 0
    assert profile_gpa4(make_profile()) == 3.8


def test_questionnaire_requires_every_answer_and_valid_scale():
    for invalid in [{}, {**answers(), 'R1': 5}, {**answers(), 'R1': True}, {**answers(), 'unexpected': 1}]:
        with pytest.raises(ValidationError):
            HollandAssessment(answers=invalid)


def test_interests_refine_selected_majors():
    a = answers(0)
    for q in questionnaire()['questions']:
        if q['dimension'] in ['I', 'R']:
            a[q['id']] = 4
    h = HollandAssessment(answers=a)
    assert scores(h)['I'] == 1
    assert scores(h)['A'] == 0
    p = make_profile(holland=h, majors=['engineering', 'design'])
    assert interest_fit(p, make_uni(majors=['engineering'])) > interest_fit(p, make_uni(majors=['design']))
    assert interest_fit(p, make_uni(majors=['medicine'])) is None
    assert interest_fit(make_profile(), make_uni()) is None
