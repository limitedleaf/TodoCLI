import sys
import os

def new():
    
    state = [
        [], #frames
    ]
    
    
    def add_frame(frame):
        state[0].append(frame)
        
        
    def render():
        terminal_size = os.get_terminal_size()
        columns, lines = terminal_size.columns, terminal_size.lines
        
        output = ""
    
        for frame in reversed(state[0]):
            
            if not frame["is_initialized"]():
                if not frame["init"]():
                    continue
                                    
            pos = frame["get_position"]()
            x_scale, y_scale = pos["get"]()
            
            size = frame["get_size"]()
            size_x, size_y = size["get"]()
            
            # Floor the scale and add 1 because ansi used a 1 based system
            x = int(columns * x_scale) + 1
            y = int(lines * y_scale) + 1         
            
            content = frame["get_content"]()
            
            for i in range(size_y):
                y_offsetted = y + i
                output += "\033[{};{}H".format(y_offsetted, x) + content[i]     

        sys.stdout.write("\033[3J\033[2J\033[H\033[?25l" + output)
        sys.stdout.flush()
    
        
    return {
        "id": "renderer",
        "add_frame": add_frame,
        "render": render
    }