from src.core import vector2d
from src.interface import render_item
from src.interface import renderer


def main():
    
    test_obj = render_item.new()
    render_item.set_name(test_obj, "Test Object")
    render_item.set_mesh(test_obj, "x" * 25)
    render_item.set_position(test_obj, vector2d.new(0.5, 0.5))
    render_item.set_size(test_obj, vector2d.new(5, 5))
    render_item.set_centralized(test_obj, True)

    renderer.add(test_obj)
    
    while True:
        renderer.render()