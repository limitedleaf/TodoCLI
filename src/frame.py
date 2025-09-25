from src import vector2
from src import renderer

def new(content = []):
    
    state = [
        vector2.new(0, 0),          # size
        vector2.new(0, 0),          # position
        content,                    # content
        False                       # initialized
    ]
    
    def get_size():
        return state[0]
    
    def set_size(x, y):
        state[0]["set"](x, y)
        
    def get_position():
        return state[1]
    
    def set_position(x, y):
        state[1]["set"](x, y)
    
    
    def get_content():
        return state[2]
    
    def set_content(content):
        state[2] = content
    
    def is_initialized():
        return state[3]
    
    
    def init():
        size_x, size_y = state[0]["get"]()
        content = state[2]
        
        if len(content) != size_y:
            print('content does not have the same lines as the size')
            return False
            
        for line in content:
            if len(line) != size_x:
                print("line size does not match the size specified")
                return False
            
        state[3] = True
        
        return True
            
    return {
        "id": "frame",
        "get_size": get_size,
        "set_size": set_size,
        "get_position": get_position,
        "set_position": set_position,
        "init": init,
        "get_content": get_content,
        "set_content": set_content,   
        "is_initialized": is_initialized,
    }
