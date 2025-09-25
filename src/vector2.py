def new(x, y):
    
    state = [x, y]
        
    def get():
        return state[0], state[1]
    
    
    def set_xy(x = state[0], y = state[1]):
        state[0] = x
        state[1] = y
        
    
    def add(x, y):
        return new(state[0] + x, state[1] + y)
    
        
    def sub(x, y):
        return new(state[0] - x, state[1] - y)
    
        
    def mul(x, y):
        return new(state[0] * x, state[1] * y)
    
        
    def div(x, y):
        return new(state[0] / x, state[1] / y)
    
        
    def round_xy():
        state[0] = round(state[0])
        state[1] = round(state[1])
        
        
    def copy():
        return new(state[0], state[1])
    
    
    def get_x():
        return x
    
    
    def get_y():
        return y
    
    
    def set_x(x):
        state[0] = x
        
        
    def set_y(y):
        state[1] = y
        
    
    return {
        "id": "vector2",
        "round": round_xy,
        "copy": copy,
        "get": get,
        "set": set_xy,
        "add": add,
        "sub": sub,
        "mul": mul,
        "div": div,
        "get_x": get_x,
        "get_y": get_y,
        "set_x": set_x,
        "set_y": set_y
    }