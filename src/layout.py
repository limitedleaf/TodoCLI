# Layout will take all the frames and places it where we want and change thier size and position 
# to fit the current termina size

# this funciton is used to generate the outline of the frame
def make_box(width, height, title=""):
    top = "┌" + title + "─" * (width - len(title) - 2) + "┐"
    middle = ["│" + " " * (width - 2) + "│" for _ in range(height - 2)]
    bottom = "└" + "─" * (width - 2) + "┘"
    return [top] + middle + [bottom]

# this function sets the size and position of all the frames
def update(cols, rows, frames):
    
    # Sizes
    top_bar_height=4
    bottom_bar_height=3
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