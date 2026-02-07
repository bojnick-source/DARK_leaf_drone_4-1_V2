import unittest


class SkipTest(unittest.SkipTest):
    pass


def skip(reason: str = "") -> None:
    raise SkipTest(reason)


def fail(message: str = "") -> None:
    raise AssertionError(message)
