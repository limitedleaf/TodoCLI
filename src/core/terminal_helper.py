import os;
import src.core.vector2d as vector2d

# Utils to interact with terminal

def get_terminal_size():
    size = os.get_terminal_size()
    return vector2d.new(size.columns, size.lines)

def create_buffer(size, val):
    return [val] * vector2d.area(size)
    
def cursor_home():
    print("\033[H", end="")
    
def hide_cursor():    
    print("\033[?25l", end="")
    
def show_cursor():
    print("\033[?25h", end="")
    