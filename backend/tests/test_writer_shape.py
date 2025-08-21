from src.common.models import SummaryPayload

def test_shape():
    sample = {
        "mode":"micro",
        "lay_summary":"A. B. C.",
        "headline":"X Y Z",
        "keywords":["a","b"],
        "jargon_definitions":{"term":"def"},
        "sentences":[{"text":"A.","citations":[0], "spans": []}],
        "reading_level":{"flesch_kincaid_grade":10,"flesch_reading_ease":50},
        "disclaimers":[]
    }
    SummaryPayload(**sample)
