from src import vector2
from src import renderer

# Create a frame
def new(content = []):
    
    # Default state of the frame
    state = [
        vector2.new(0, 0),          # size
        vector2.new(0, 0),          # position
        content,                    # content
        False                       # initialized
    ]
    
    # Functions to get and modify different stuff in the frame
    # Changing any of these functions will set the frame to not initialized
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
    
    # Init checks if the frame's state is valid for the renderer to process
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
    
    # We return dict of functions
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
