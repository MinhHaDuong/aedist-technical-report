
from experiments.sota.exp2_protocol_review import extract_verdict


def test_extract_verdict_tolerates_round1_code_fence_wrapper():
    narrative = "Review text\n```\nVERDICT: ACCEPT WITH RESERVATIONS\n```\n"
    assert extract_verdict(narrative) == "VERDICT: ACCEPT WITH RESERVATIONS"


def test_extract_verdict_tolerates_round2_bold_wrapper():
    narrative = "Findings\n**VERDICT: REJECT**\n"
    assert extract_verdict(narrative) == "VERDICT: REJECT"
