# Render item represents something that can be rendered

import src.core.vector2d as vector2d

def new():
    return [
        "", # Name
        "", # Mesh
        vector2d.new(), # Position
        vector2d.new(), # Size
        False, # Centralized
    ]
    
def get_name(item):
    return item[0]

def set_name(item, name):
    item[0] = name
    
    
def get_mesh(item):
    return item[1]


def set_mesh(item, mesh):
    item[1] = mesh
    
    
def get_position(item):
    return item[2]


def set_position(item, position):
    item[2] = position
    

def get_size(item):
    return item[3]


def set_size(item, scale):
    item[3] = scale
    

def get_centralized(item):
    return item[4]

def set_centralized(item, centralized):
    item[4] = centralized
    
