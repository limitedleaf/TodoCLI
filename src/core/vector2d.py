# Simple 2d vector data type
# Can be used to store postion, velocites etc.

def new(x = 0, y = 0):
    return [x, y]

def x(a):
    return a[0]

def half():
    return [0.5, 0.5]

def y(a):
    return a[1]

def set(a, x, y):
    a[0] = x
    a[1] = y
    
def set_x(a, x):
    a[0] = x
    
def set_y(a, y):
    a[1] = y
    
def area(a):
    return a[0] * a[1]

def add(a, b):
    return [a[0] + b[0], a[1] + b[1]]
    

def sub(a, b):
    return [a[0] - b[0], a[1] - b[1]]


def mul(a, b):
    return [a[0] * b[0], a[1] * b[1]]


def div(a, b):
    return [a[0] / b[0], a[1] / b[1]]


def floor_mul(a, b):
    return [int(a[0] * b[0]), int(a[1] * b[1])]


def floor_div(a, b):
    return [int(a[0] / b[0]), int(a[1] / b[1])]


def round_mul(a, b):
    return [round(a[0] * b[0]), round(a[1] * b[1])]

def scale(a, scale):
    return [a[0] * scale, a[1] * scale]


# Convert a 2d coordinate to a 1d coordinate
def flatten(a, x_size):
    return a[1] * x_size + a[0]