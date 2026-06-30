"""Shared test fixture for pychronicle.ast_parser.

This fixture is intentionally minimal and line-numbered to match the
expected results in test/test_ast_parser.py.
"""
































total = 0
for i in range(2):
    total = total + i
    squared = i * i



x = 1
y = x * 2

a, b = 1, 2

c = d = 10

items = [1, 2, 3]
items[0] = 99  # subscript assignment — should be skipped

# for i in range(1, 6):          # Outer loop
#     for j in range(1, 6):      # Inner loop
#         s= i*j # Print product with tab space

