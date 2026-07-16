import ast

# Study each type one at a time — run each block separately

# Type 1: Regular assignment — ast.Assign (already handled)
print("=== Regular: x = 5 ===")
print(ast.dump(ast.parse("x = 5"), indent=2))
# Key fields: .targets (LIST), .value

# Type 2: Augmented assignment — NOT currently handled
print("\n=== Augmented: x += 1 ===")
print(ast.dump(ast.parse("x += 1"), indent=2))
# Key fields: .target (SINGULAR, no list), .op, .value
# Important: target is NOT targets — easy to miss this

# Type 3: Annotated assignment — NOT currently handled
print("\n=== Annotated: x: int = 5 ===")
print(ast.dump(ast.parse("x: int = 5"), indent=2))
# Key fields: .target (singular), .annotation, .value
# Note: .value can be None if it's just a declaration (x: int)

# Type 4: For-loop variable — NOT currently handled
print("\n=== For loop: for i in range(n) ===")
print(ast.dump(ast.parse("for i in range(3): pass"), indent=2))
# Key fields: .target (the loop variable), .iter (the iterable)
# i is bound here, NOT in an Assign node — that's why it's invisible now