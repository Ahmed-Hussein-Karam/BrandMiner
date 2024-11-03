import os

import random
import numpy as np
from PIL import Image
from moviepy.editor import ImageSequenceClip
from pathlib import Path

# Literals
BRAND = 'brand'
SCENE = 'scene'
EMPTY = 'empty'

# Video Parameters
hours = 0.02
sec_per_hr = 3600
frames_per_sec = 3
frame_count =  int(hours * sec_per_hr * frames_per_sec)
frame_size_px = 300
grid_size = (9, 9)

cell_count = grid_size[0] * grid_size[1]
cell_size = frame_size_px // grid_size[0]  # Size of each cell in the grid
cell_types = [BRAND, SCENE, EMPTY]
cell_types_probabilities = [0.1, 0.8, 0.1]

# When a cell ttl expires, a new random ttl is set for that cell
cell_ttl = [0 for _ in range(cell_count)]

# Constants
max_cell_ttl = frames_per_sec * 2
max_enabled_brands_per_video = 5
max_imgs_per_brand = 5

# Paths
base_path = os.getcwd()
img_path = os.path.join(base_path, 'img')

brands_path = os.path.join(img_path, 'brands')
scenes_path = os.path.join(img_path, 'scenes')

scene_types = [str(d) for d in Path(scenes_path).iterdir() if d.is_dir()]
all_brands = [str(d) for d in Path(brands_path).iterdir() if d.is_dir()]

brands_count = random.randint(1, min(len(all_brands), max_enabled_brands_per_video))
brands = random.sample(all_brands, brands_count)

brand_imgs = {f'{b}': random.sample([f for f in Path(os.path.join(brands_path, b)).iterdir() if f.is_file()], max_imgs_per_brand) for b in brands}
scene_imgs = {f'{s}': [f for f in Path(os.path.join(scenes_path, s)).iterdir() if f.is_file()] for s in scene_types}

# Colors
background_color = (255, 255, 255)
line_color = (0, 0, 0)

img_cache = {}

def generate_random_grid(current_grid):
    """Generates a random grid with each cell is 'brand', 'scene', or empty."""
    for i in range(cell_count):
        if cell_ttl[i] > 0:
            cell_ttl[i] -= 1
            continue

        cell_ttl[i] = random.randint(1, max_cell_ttl)
        current_grid[i] = random.choices(cell_types, weights=cell_types_probabilities, k=1)[0]

        if current_grid[i] == BRAND:
            random_brand = random.choice(brands)
            current_grid[i] = random.choice(brand_imgs[random_brand])
        elif current_grid[i] == SCENE:
            random_scene_type = random.choice(scene_types)
            current_grid[i] = random.choice(scene_imgs[random_scene_type])
    
    return current_grid

def draw_frame(grid):
    """Draws a single frame of the tic-tac-toe grid using image files for 'X' and 'O'."""
    img = Image.new('RGB', (frame_size_px, frame_size_px), background_color)

    for row in range(grid_size[0]):
        for col in range(grid_size[1]):
            cell_value = grid[row * grid_size[1] + col]
            if cell_value != EMPTY:
                if cell_value in img_cache:
                    img.paste(img_cache[cell_value], (col * cell_size, row * cell_size), img_cache[cell_value])
                else:
                    cell_img = Image.open(cell_value).convert('RGBA').resize((cell_size, cell_size))
                    img_cache[cell_value] = cell_img

                    img.paste(cell_img, (col * cell_size, row * cell_size), cell_img)
    return img

# Generate all frames
frames = []
initial_grid = [EMPTY for _ in range(cell_count)]

print (f"Frame count: {frame_count}")
for i in range(frame_count):
    print (f"Frame#: {i}")
    grid = generate_random_grid(initial_grid)
    frame = draw_frame(grid)
    frames.append(np.array(frame))  # Convert to NumPy array

# Convert frames to an MP4 video
clip = ImageSequenceClip(frames, fps=frames_per_sec)
clip.write_videofile("movie.mp4", codec="libx264")
