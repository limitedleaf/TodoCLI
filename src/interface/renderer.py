# Renderer handles taking objects and rendering them into the terminal

import src.core.terminal_helper as terminal_helper
import src.core.vector2d as vector2d
import src.interface.render_item as render_item

render_stack = []

# We render items in FIFO order
def add(item):
    render_stack.append(item)
    

# Used to centralize the item's position to the center of item
def centralize(item, item_position):
    size = render_item.get_size(item)
    half_size = vector2d.round_mul(size, vector2d.half())
    return vector2d.sub(item_position, half_size)

# Used to apply the item's position_scale
def apply_position(item, terminal_size):
    return vector2d.round_mul(terminal_size, render_item.get_position(item))


def get_1d(x, y, width):
    return x + (y * width)

def render():
    terminal_size = terminal_helper.get_terminal_size()
    terminal_width = vector2d.x(terminal_size)
    terminal_height = vector2d.y(terminal_size)

    buffer = terminal_helper.create_buffer(terminal_size, " ")

    for item in reversed(render_stack):
        position = apply_position(item, terminal_size)
        if render_item.get_centralized(item):
            position = centralize(item, position)

        mesh = render_item.get_mesh(item)
        size = render_item.get_size(item)
        width = vector2d.x(size)
        height = vector2d.y(size)

        for y in range(height):
            buf_y = int(vector2d.y(position) + y)
            if buf_y < 0 or buf_y >= terminal_height:
                continue

            buf_start = get_1d(int(vector2d.x(position)), buf_y, terminal_width)
            buf_end = buf_start + width

            mesh_start = get_1d(0, y, width)
            mesh_end = mesh_start + width

            buffer[buf_start:buf_end] = mesh[mesh_start:mesh_end]

    terminal_helper.cursor_home()
    terminal_helper.hide_cursor()

    print("".join(buffer), end="")