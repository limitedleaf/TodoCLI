from src import renderer
from src import frame as fr
import os
import time

FRAME_TIME = 1/24

def make_box(width, height, title=""):
    top = "┌" + title + "─" * (width - len(title) - 2) + "┐"
    middle = ["│" + " " * (width - 2) + "│" for _ in range(height - 2)]
    bottom = "└" + "─" * (width - 2) + "┘"
    return [top] + middle + [bottom]


def layout(cols, rows, frames, top_bar_height=4, bottom_bar_height=3):
    # Sizes
    left_width = cols // 3
    right_width = cols - left_width - 1

    top_height = rows // 2
    bottom_height = rows - top_height

    main_editor_height = rows - top_bar_height - bottom_bar_height

    # Left panels
    left_top = frames[0]
    left_top["set_size"](left_width, top_height)
    left_top["set_position"](0, 0)
    left_top["set_content"](make_box(left_width, top_height, "Select-Topic"))

    left_bottom = frames[1]
    left_bottom["set_size"](left_width, bottom_height)
    left_bottom["set_position"](0, top_height / rows)
    left_bottom["set_content"](make_box(left_width, bottom_height, "Select-Todo"))

    # Right panels
    top_bar = frames[2]
    top_bar["set_size"](right_width, top_bar_height)
    top_bar["set_position"]((left_width + 1) / cols, 0)
    top_bar["set_content"](make_box(right_width, top_bar_height, "Todo-Info"))

    editor = frames[3]
    editor["set_size"](right_width, main_editor_height)
    editor["set_position"]((left_width + 1) / cols, top_bar_height / rows)
    editor["set_content"](make_box(right_width, main_editor_height, "Notes"))

    bottom_bar = frames[4]
    bottom_bar["set_size"](right_width, bottom_bar_height)
    bottom_bar["set_position"]((left_width + 1) / cols, (top_bar_height + main_editor_height) / rows)
    bottom_bar["set_content"](make_box(right_width, bottom_bar_height, "Status"))

    return [left_top, left_bottom, top_bar, editor, bottom_bar]



def main():
    os.system("cls")

    main_renderer = renderer.new()
    
    frames = []
    
    for _ in range(5):
        frames.append(fr.new())
    
    prev_cols, prev_rows = os.get_terminal_size().columns, os.get_terminal_size().lines
    
    layout(prev_cols, prev_rows, frames)
    
    for frame in frames:
        main_renderer["add_frame"](frame)
        
    main_renderer["render"]()

    
    while True:
        start = time.perf_counter()
        
        curr_size = os.get_terminal_size()
        if prev_cols != curr_size.columns or prev_rows != curr_size.lines:
            layout(curr_size.columns, curr_size.lines, frames)
            prev_cols, prev_rows = curr_size.columns, curr_size.lines
            
        end = time.perf_counter()
        
        elapsed = end - start
        
        diff = FRAME_TIME - elapsed
        if diff > 0:
            time.sleep(diff)
        
        main_renderer["render"]()
