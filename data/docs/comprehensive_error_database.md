# Python Error Troubleshooting Reference Database

This guide details common python errors, typical causes, code examples of the failure, and their corresponding solutions.

---

## 1. SyntaxError & IndentationError (Syntax Issues)

### Description
These errors are raised when the Python parser encounters code that does not follow Python's grammatical structure. They occur prior to execution.

### Common Causes
- Missing colons (`:`) at the end of function signatures, `if`, `for`, `while`, or `class` definitions.
- Mismatched or unclosed brackets, parentheses, or quotes (`( )`, `[ ]`, `{ }`, `' '`, `" "`).
- Inconsistent indentation (mixing tabs and spaces, or uneven spacing blocks).

### Examples & Fixes
*Incorrect:*
```python
def check_value(x)
if x > 5
print("Greater")
```

*Correct:*
```python
def check_value(x):
    if x > 5:
        print("Greater")
```

---

## 2. TypeError (Type Mismatch & Call Errors)

### Description
Raised when an operation or function is applied to an object of an inappropriate type.

### Common Causes
- Attempting to add, concatenate, or compare incompatible types (e.g., `str` and `int`).
- Accessing or subscripting objects that do not support indexing (like calling `x[0]` on an `int` or `NoneType`).
- Calling a non-callable object (like `x = 5; x()`).
- Forgetting to pass required arguments or passing the wrong types to a function.

### Examples & Fixes
*Incorrect:*
```python
age = "25"
next_year = age + 1  # TypeError: can only concatenate str (not "int") to str
```

*Correct:*
```python
age = "25"
next_year = int(age) + 1
```

*Incorrect:*
```python
# 'NoneType' object is not subscriptable
data = None
val = data["key"]
```

*Correct:*
```python
data = {"key": "value"}
val = data["key"] if data else None
```

---

## 3. IndexError & KeyError (Index & Access Errors)

### Description
Raised when attempting to access elements outside valid sequences (lists, tuples, strings) or querying missing keys from mappings (dictionaries).

### Common Causes
- Off-by-one errors (accessing index `len(arr)` instead of `len(arr) - 1`).
- Empty list access or pop.
- Accessing dictionary keys without verifying they exist.

### Examples & Fixes
*Incorrect:*
```python
colors = ["red", "green"]
selected = colors[2]  # IndexError: list index out of range
```

*Correct:*
```python
colors = ["red", "green"]
if len(colors) > 2:
    selected = colors[2]
else:
    selected = "default"
```

*Incorrect:*
```python
user = {"name": "Alice"}
role = user["role"]  # KeyError: 'role'
```

*Correct:*
```python
user = {"name": "Alice"}
role = user.get("role", "guest")  # Safe dictionary lookup
```

---

## 4. NameError, AttributeError & ValueError (Runtime Issues)

### Description
Errors encountered during active runtime due to missing symbols, attributes, or incorrect data representations.

### Common Causes
- Typo in a variable name, or using a variable before it has been initialized/imported.
- Invoking a method that does not exist on a specific object type (e.g., calling `append()` on a dictionary).
- Passing arguments of correct type but invalid values (e.g., parsing `int("abc")`).

### Examples & Fixes
*Incorrect:*
```python
num = int("123a")  # ValueError: invalid literal for int()
```

*Correct:*
```python
raw_input = "123a"
if raw_input.isdigit():
    num = int(raw_input)
else:
    num = 0
```

*Incorrect:*
```python
my_data = {"a": 1}
my_data.append(2)  # AttributeError: 'dict' object has no attribute 'append'
```

*Correct:*
```python
my_data = {"a": 1}
my_data["b"] = 2
```

---

## 5. RecursionError & ZeroDivisionError (Control Flow Issues)

### Description
Structural coding mistakes that fail mathematical restrictions or break stack execution limits.

### Common Causes
- Missing base-case termination inside recursive methods, leading to stack overflow.
- Dividing any numerical value by zero.

### Examples & Fixes
*Incorrect:*
```python
def factorial(n):
    return n * factorial(n - 1)  # RecursionError: maximum recursion depth exceeded
```

*Correct:*
```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```
