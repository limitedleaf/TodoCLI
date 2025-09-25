# The renderer is responsible for taking frames and rendering them to the terminal based on thier
# position and size

import sys
import os


def new():
    
    # We have a list of frames that need to be rendered
    state = [
        [], #frames
    ]
    
    # this function is used to add a frame to the list of frames to be rendered
    def add_frame(frame):
        state[0].append(frame)
        
    
    # main function that takes all the frames and renders them
    def render():
        # We first get the size of the terminal
        terminal_size = os.get_terminal_size()
        columns, lines = terminal_size.columns, terminal_size.lines
        
        # The final output that should be in the terminal
        output = ""
    
        # We loop through all the frames in reversed so that the frame added last will override
        # any frames below it if there is an overlap
        for frame in reversed(state[0]):
            
            # We check if the frame is initalized if not we try to initalize it
            if not frame["is_initialized"]():
                if not frame["init"]():
                    continue
                
            # We get the position and size of the frame   
            pos = frame["get_position"]()
            x_scale, y_scale = pos["get"]()
            
            size = frame["get_size"]()
            _, size_y = size["get"]()
            
            # The position is scale and an absolute value like for example 
            # if the position is (0.5, 0.5) (it can be b/w 0 and 1) and terminal size is 10
            # the frame will be at 5, 5
            # we floor it with(int) because we need it to be in integers not decimals
            # we add one because ascii terminal start from 1 and not 0 but we start from 0
            x = int(columns * x_scale) + 1
            y = int(lines * y_scale) + 1         
            
            # we get the content of the frame
            # the content of the frame is the stuff each frame contains
            # its a list with a string for each line of the frame
            # Example:
            # [
            #    "Line1",
            #    "Line2"
            # ]
            content = frame["get_content"]()
            
            # We loop through each line of the frame and add it to the output
            for i in range(size_y):
                # Basically a terminal is made up of rows and columns
                # by using "\033{ROW}:{COLUMN}H" we can move the cursor to a specific position
                # and then anything after it will be printed at that position
                y_offsetted = y + i
                output += "\033[{};{}H".format(y_offsetted, x) + content[i]     

        # sys.stdout.write is just print but it doesn't immediately print and stores the data
        # and only prints when we call .flush it also doesn't do stuf like formating and other stuff
        
        # \033[3J\033[2J\033[H will clear the terminal hide the cursor and move the cursor to the top
        sys.stdout.write("\033[3J\033[2J\033[H\033[?25l" + output)
        sys.stdout.flush()
    
        
    return {
        "id": "renderer",
        "add_frame": add_frame,
        "render": render
    }