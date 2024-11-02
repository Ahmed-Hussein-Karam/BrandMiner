import os

import random
import numpy as np
from PIL import Image, ImageDraw
from moviepy.editor import ImageSequenceClip
from pathlib import Path

# Video Parameters
hours = 0.02
sec_per_hr = 3600
frames_per_sec = 3
frame_count =  int(hours * sec_per_hr * frames_per_sec)
grid_size = (9, 9)
cell_count = grid_size[0] * grid_size[1]

# Dfinitions and Constants
max_enabled_brands_per_video = 5
max_cell_ttl = frames_per_sec * 2
cell_types = ['brand', 'scene', 'empty']
cell_types_probabilities = [0.2, 0.7, 0.1]

# When a cell ttl expires, a new random ttl is set for this cell
cell_ttl = [0 for _ in range(cell_count)]

frame_size_px = 300
cell_size = frame_size_px // grid_size[0]  # Size of each cell in the grid

# Paths
base_path = os.getcwd()
img_path = os.path.join(base_path, 'img')
empty_img_path = os.path.join(img_path,'empty.png')
empty_img = Image.open(empty_img_path).convert("RGBA").resize((cell_size, cell_size))

brands_path = os.path.join(img_path, 'brands')
scenes_path = os.path.join(img_path, 'scenes')

scene_types = [str(d) for d in Path(scenes_path).iterdir() if d.is_dir()]
all_brands = [str(d) for d in Path(brands_path).iterdir() if d.is_dir()]

brands_count = random.randint(1, min(len(all_brands), max_enabled_brands_per_video))
brands = random.sample(all_brands, brands_count)

brand_imgs = {f'{b}': [f for f in Path(os.path.join(brands_path, b)).iterdir() if f.is_file()] for b in brands}
scene_imgs = {f'{s}': [f for f in Path(os.path.join(scenes_path, s)).iterdir() if f.is_file()] for s in scene_types}

# Colors
background_color = (255, 255, 255)
line_color = (0, 0, 0)

def generate_random_grid(current_grid):
    """Generates a random grid with each cell is 'brand', 'scene', or empty."""
    for i in range(cell_count):
        if cell_ttl[i] > 0:
            cell_ttl[i] -= 1
            continue

        cell_ttl[i] = random.randint(1, max_cell_ttl)
        current_grid[i] = random.choices(cell_types, weights=cell_types_probabilities, k=1)[0]

        if current_grid[i] == 'brand':
            random_brand = random.choice(brands)
            current_grid[i] = random.choice(brand_imgs[random_brand])
        elif current_grid[i] == 'scene':
            random_scene_type = random.choice(scene_types)
            current_grid[i] = random.choice(scene_imgs[random_scene_type])
    
    return current_grid

def draw_frame(grid):
    """Draws a single frame of the tic-tac-toe grid using image files for 'X' and 'O'."""
    img = Image.new("RGB", (frame_size_px, frame_size_px), background_color)
    draw = ImageDraw.Draw(img)

    # Draw the grid lines
    for i in range(1, grid_size[0]):  # Draw grid lines
        draw.line((i * cell_size, 0, i * cell_size, frame_size_px), fill=line_color, width=3)
        draw.line((0, i * cell_size, frame_size_px, i * cell_size), fill=line_color, width=3)

    for row in range(grid_size[0]):
        for col in range(grid_size[1]):
            cell_value = grid[row * grid_size[1] + col]
            if cell_value == 'empty':
                img.paste(empty_img, (col * cell_size, row * cell_size), empty_img)
            else:
                cell_img = Image.open(cell_value).convert("RGBA").resize((cell_size, cell_size))
                img.paste(cell_img, (col * cell_size, row * cell_size), cell_img)
    return img

# Generate all frames
frames = []
initial_grid = ['empty' for _ in range(cell_count)]

print (f"Frame count: {frame_count}")
for i in range(frame_count):
    print (f"Frame#: {i}")
    grid = generate_random_grid(initial_grid)
    frame = draw_frame(grid)
    frames.append(np.array(frame))  # Convert to NumPy array

# Convert frames to an MP4 video
clip = ImageSequenceClip(frames, fps=frames_per_sec)
clip.write_videofile("movie.mp4", codec="libx264")
