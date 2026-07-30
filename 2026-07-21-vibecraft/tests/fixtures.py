"""Test fixtures for vibecraft tests."""

CLEAN_PYTHON = '''
def greet(name: str) -> str:
    """Return a greeting for the given name."""
    return f"Hello, {name}"


def add(a: int, b: int) -> int:
    """Add two integers and return the result."""
    return a + b


class Calculator:
    """A simple calculator."""

    def multiply(self, x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y
'''

VIBE_CODED_PYTHON = '''
def process(x):
    try:
        result = x / 0
    except:
        pass
    print("done")
    TODO
    return 42
'''

BARE_EXCEPT_CODE = '''
def dangerous():
    try:
        x = 1 / 0
    except:
        pass
'''

EXCEPT_PASS_CODE = '''
def silent():
    try:
        pass
    except ValueError:
        pass
'''

DEEP_NESTING_CODE = '''
def deeply(x):
    if x:
        if x > 0:
            if x > 10:
                if x > 100:
                    print(x)
'''

LONG_FUNCTION_CODE = """
def long_function():
    a = 1
    b = 2
    c = 3
    d = 4
    e = 5
    f = 6
    g = 7
    h = 8
    i = 9
    j = 10
    k = 11
    l = 12
    m = 13
    n = 14
    o = 15
    p = 16
    q = 17
    r = 18
    s = 19
    t = 20
    u = 21
    v = 22
    w = 23
    x = 24
    y = 25
    z = 26
    aa = 27
    ab = 28
    ac = 29
    ad = 30
    ae = 31
    af = 32
    ag = 33
    ah = 34
    ai = 35
    aj = 36
    ak = 37
    al = 38
    am = 39
    an = 40
    ao = 41
    ap = 42
    aq = 43
    ar = 44
    as_val = 45
    at = 46
    au = 47
    av = 48
    aw = 49
    return aw
"""

MISSING_DOCSTRING_CODE = '''
def public_function():
    return 42

class PublicClass:
    def method(self):
        return True
'''

MAGIC_STRING_CODE = '''
def get_status():
    return "PENDING_APPROVAL_STATUS_V2"
'''

MAGIC_NUMBER_CODE = '''
def calculate():
    return 86400 * 30
'''

HARDCODE_URL_CODE = '''
def fetch_data():
    url = "https://api.example.com/v2/users"
    return url
'''

CONSISTENT_SNAKE = '''
def get_user_id():
    return 1

def calculate_total():
    return 100
'''

INCONSISTENT_NAMING = '''
def getUserId():
    return 1

def calculate_total():
    return 100

class MyClass:
    def myMethod(self):
        pass
'''