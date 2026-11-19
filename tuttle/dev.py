import functools


def singleton(cls):
    """A decorator to turn a class into a singleton class (only one instance)."""
    instances = {}

    @functools.wraps(cls)
    def getinstance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return getinstance
