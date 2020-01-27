from json_syntax import helpers as hlp


def test_identity():
    "Test that the identity function does what it says."

    subj = object()

    assert hlp.identity(subj) is subj
