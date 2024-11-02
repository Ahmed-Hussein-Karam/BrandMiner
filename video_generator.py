import random
import numpy as np
from PIL import Image, ImageDraw
from moviepy.editor import ImageSequenceClip

# Parameters
hours = 0.25
sec_per_hr = 3600
frames_per_sec = 3
frame_count =  int(hours * sec_per_hr * frames_per_sec)
grid_size = (9, 9)
frame_size = 300  # Size of each frame in pixels (300x300)
cell_size = frame_size // grid_size[0]  # Size of each cell in the grid

# Colors and files
background_color = (255, 255, 255)
line_color = (0, 0, 0)
X_img = Image.open("img/X.png").convert("RGBA").resize((cell_size, cell_size))
O_img = Image.open("img/O.png").convert("RGBA").resize((cell_size, cell_size))

def generate_random_grid():
    """Generates a random grid with 'X', 'O', or empty."""
    symbols = ['X', 'O', '']
    return [random.choice(symbols) for _ in range(grid_size[0] * grid_size[1])]

def draw_frame(grid):
    """Draws a single frame of the tic-tac-toe grid using image files for 'X' and 'O'."""
    img = Image.new("RGB", (frame_size, frame_size), background_color)
    draw = ImageDraw.Draw(img)

    # Draw the grid lines
    for i in range(1, grid_size[0]):  # Draw grid lines
        draw.line((i * cell_size, 0, i * cell_size, frame_size), fill=line_color, width=3)
        draw.line((0, i * cell_size, frame_size, i * cell_size), fill=line_color, width=3)

    # Place 'X' and 'O' images in each cell
    for row in range(grid_size[0]):
        for col in range(grid_size[1]):
            symbol = grid[row * grid_size[1] + col]
            if symbol == 'X':
                img.paste(X_img, (col * cell_size, row * cell_size), X_img)
            elif symbol == 'O':
                img.paste(O_img, (col * cell_size, row * cell_size), O_img)

    return img

# Generate all frames
frames = []
for i in range(frame_count):
    grid = generate_random_grid()
    frame = draw_frame(grid)
    frames.append(np.array(frame))  # Convert to NumPy array

# Convert frames to an MP4 video
clip = ImageSequenceClip(frames, fps=frames_per_sec)
clip.write_videofile("tic_tac_toe.mp4", codec="libx264")
