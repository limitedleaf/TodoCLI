from src import renderer
from src import frame as fr
from src import layout
import os
import time

FRAME_TIME = 1/24

# The project is setup so this function get called when we run the project
def main():
    
    # Clear the terminal of any previous text
    os.system("cls")

    # Create a new renderer
    main_renderer = renderer.new()
    
    # Create 5 frames to use in our layout
    frames = []
    
    for _ in range(5):
        frames.append(fr.new())
    
    # Generate the intial layout at the terminal start up size
    prev_cols, prev_rows = os.get_terminal_size().columns, os.get_terminal_size().lines
    
    layout.update(prev_cols, prev_rows, frames)
    
    # Add the frames to the renderer
    for frame in frames:
        main_renderer["add_frame"](frame)
    
    # Render the first frame
    main_renderer["render"]()

    # We loop infinitely to keep our app open
    # We fix the number of times we check for changes with  FRAME_TIME
    # Everytime we check how long it takes for the loop to run
    # Then we sub that and frame time and we halt execution for that time
    # In short the if frame time is 1/24 the code inside loop only runs 24 times a second
    while True:
        start = time.perf_counter()
        
        # We check if the terminal size has changed if it has then 
        curr_size = os.get_terminal_size()
        if prev_cols != curr_size.columns or prev_rows != curr_size.lines:
            layout.update(curr_size.columns, curr_size.lines, frames)
            prev_cols, prev_rows = curr_size.columns, curr_size.lines
            
        end = time.perf_counter()
        
        elapsed = end - start
        
        diff = FRAME_TIME - elapsed
        if diff > 0:
            time.sleep(diff)
        
        main_renderer["render"]()
