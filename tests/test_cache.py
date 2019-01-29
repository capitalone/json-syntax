from json_syntax import cache


def test_forward_action():
    "Test that ForwardAction can replace a function and be updated."

    def func1(a, b):
        return a + b

    def func2(a, b):
        "Doc string."
        return a * b

    subj = cache.ForwardAction(func1)

    assert subj(3, 7) == 10

    subj.__call__ = func2

    assert subj(3, 7) == 21

    assert subj.__name__ == "func2"
    assert subj.__doc__ == "Doc string."
    assert getattr(subj, "bogus", "missing") == "missing"


def test_simple_cache_get():
    "Test that SimpleCache handles a cache miss."

    subj = cache.SimpleCache()

    assert subj.get(verb="verb", typ=int) is None


def test_simple_cache_flight():
    "Test that the SimpleCache inflight -> complete mechanism produces a valid forward action."

    subj = cache.SimpleCache()

    # Notify the cache that we're working on the result.
    subj.inflight(verb="verb", typ=int)

    # Another rule needs the result before it's ready.
    actual = subj.get(verb="verb", typ=int)

    def action(value):
        return value * 10

    # The ForwardAction previously set is loaded with the callable.
    subj.complete(verb="verb", typ=int, action=action)

    # The ForwardAction is loaded with the action.
    assert actual(5) == 50

    # The cache entry is replaced with the action itself.
    assert subj.get(verb="verb", type=int) is action


def test_simple_cache_unhashable():
    pass
