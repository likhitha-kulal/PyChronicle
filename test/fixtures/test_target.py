"""Shared test fixture for pychronicle.ast_parser."""


def compute():
    total = 0
    for i in range(2):
        total = total + i
        squared = i * i
    return total,squared

x = compute()
y = x * 2

a, b = 1, 2
c = d = 10

items = [1, 2, 3]
items[0] = 99  # subscript - should be skipped
