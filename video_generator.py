import os

import random
import numpy as np
from PIL import Image
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioClip
from pathlib import Path

################################## VIDEO GENERATION ##################################

# Literals
BRAND = 'brand'
SCENE = 'scene'
EMPTY = 'empty'

# Video Parameters
hours = 0.02
sec_per_hr = 3600
duration_sec = int(hours * sec_per_hr)
frames_per_sec = 3
frame_count =  duration_sec * frames_per_sec
frame_size_px = 300
grid_size = (9, 9)

cell_count = grid_size[0] * grid_size[1]
cell_size = frame_size_px // grid_size[0]  # Size of each cell in the grid
cell_types = [BRAND, SCENE, EMPTY]
cell_types_probabilities = [0.05, 0.8, 0.15]

# When a cell ttl expires, a new random ttl is set for that cell
cell_ttl = [0 for _ in range(cell_count)]

# Constants
max_cell_ttl = frames_per_sec * 2
max_enabled_brands_per_video = 5
max_brands_per_frame = 2

# Paths
base_path = os.getcwd()
media_path = os.path.join(base_path, 'media')

brands_path = os.path.join(media_path, 'brands')
scenes_path = os.path.join(media_path, 'scenes')

scene_types = [d.name for d in Path(scenes_path).iterdir() if d.is_dir()]
all_brands = [d.name for d in Path(brands_path).iterdir() if d.is_dir()]

brands_count = random.randint(1, min(len(all_brands), max_enabled_brands_per_video))
brands = random.sample(all_brands, brands_count)

# Used to track where the brand was rendered on the screen,
# where -1 means not rendered
brand_cell_indices = {f'{b}': [-1] for b in brands}

brand_imgs = {f'{b}': [f for f in Path(os.path.join(brands_path, b)).iterdir() if f.is_file()] for b in brands}
scene_imgs = {f'{s}': [f for f in Path(os.path.join(scenes_path, s)).iterdir() if f.is_file()] for s in scene_types}

# Colors
background_color = (255, 255, 255)
line_color = (0, 0, 0)

img_cache = {}

def generate_random_grid(current_grid, current_img_paths):
    """Generates a random grid with each cell is 'brand', 'scene', or empty."""
    random_cell_types = random.choices(cell_types, weights=cell_types_probabilities, k=cell_count)

    grid_brands_count = sum(
        1
        for i in range(len(current_grid))
        if current_grid[i] == BRAND and cell_ttl[i] > 0
    )

    # Loop cells in random order
    for i in random.sample(range(0, cell_count), cell_count):
        if cell_ttl[i] > 0:
            cell_ttl[i] -= 1
            continue

        # When Brand ttl expires, set cell index to -1 (disappear)
        if current_grid[i] == BRAND:
            for b in brands:
                if brand_cell_indices[b][-1] == i: 
                    brand_cell_indices[b].append(-1)
                    break

        cell_ttl[i] = random.randint(1, max_cell_ttl)
        current_grid[i] = random_cell_types[i]

        if current_grid[i] == EMPTY:
            current_img_paths[i] = None
        elif current_grid[i] == BRAND and grid_brands_count < max_brands_per_frame:
            # Pick a brand that is not already rendered
            random_brand = random.choice([b for b in brands if brand_cell_indices[b][-1] == -1])

            brand_cell_indices[random_brand].append(i)
            current_img_paths[i] = random.choice(brand_imgs[random_brand])

            grid_brands_count += 1
        else:
            current_grid[i] = SCENE
            random_scene_type = random.choice(scene_types)
            current_img_paths[i] = random.choice(scene_imgs[random_scene_type])
    
    return (current_grid, current_img_paths)

def draw_frame(grid_img_paths):
    """Draws a single frame of the tic-tac-toe grid using image files for 'X' and 'O'."""
    img = Image.new('RGB', (frame_size_px, frame_size_px), background_color)

    for row in range(grid_size[0]):
        for col in range(grid_size[1]):
            cell_value = grid_img_paths[row * grid_size[1] + col]
            if cell_value != None:
                if cell_value in img_cache:
                    img.paste(img_cache[cell_value], (col * cell_size, row * cell_size), img_cache[cell_value])
                else:
                    cell_img = Image.open(cell_value).convert('RGBA').resize((cell_size, cell_size), Image.LANCZOS)
                    img_cache[cell_value] = cell_img

                    img.paste(cell_img, (col * cell_size, row * cell_size), cell_img)
    return img

def gen_video(audio):
    # Generate all frames
    frames = []
    grid = [EMPTY for _ in range(cell_count)]
    grid_img_paths = [None for _ in range(cell_count)]

    print (f"Frame count: {frame_count}")
    for i in range(frame_count):
        print (f"Frame#: {i}")
        (grid, grid_img_paths) = generate_random_grid(grid, grid_img_paths)
        frame = draw_frame(grid_img_paths)
        frames.append(np.array(frame))  # Convert to NumPy array

    # Convert frames to an MP4 video
    video_clip = ImageSequenceClip(frames, fps=frames_per_sec)

    return video_clip.set_audio(audio)

################################## AUDIO GENERATION ##################################

# Standard audio value
audio_fps = 44100

brand_audio = {f'{b}': AudioFileClip(str([f for f in Path(os.path.join(brands_path, os.path.join(b, 'audio'))).iterdir() if f.is_file()][0])).set_fps(audio_fps) for b in brands}
random_statement_audio = AudioFileClip(os.path.join(media_path, 'random_statement.mp3')).set_fps(audio_fps)

min_silence_duration_sec = min(5, duration_sec - 2)
max_silence_duration_sec = min(60, duration_sec)

def create_silent_clip():
    clip_duration_sec = random.randint(min_silence_duration_sec, max_silence_duration_sec)
    return AudioClip(lambda t: 0, duration=clip_duration_sec)

def gen_audio():
    audio_segments = []
    curr_audio_duration_sec = 0
    statement_count = 0

    while curr_audio_duration_sec < duration_sec - max_silence_duration_sec + 3:
        # Append a silent clip
        audio_segments.append(create_silent_clip())
        print (f"silent clip of {audio_segments[-1].duration} sec")

        if random.random() < 0.7:
            # Append a random statement
            audio_segments.append(random_statement_audio)
            statement_count += 1
            print (f"statement clip of {audio_segments[-1].duration} sec")
        else:
            # Append a random brand audio clip
            audio_segments.append(brand_audio[random.choice(brands)])
            print (f"brand clip of {audio_segments[-1].duration} sec")
        
        curr_audio_duration_sec += audio_segments[-1].duration + audio_segments[-2].duration

    # Concatenate all audio segments
    final_audio_clip = concatenate_audioclips(audio_segments)
    print (f"Number of statements in audio track: {len(statement_count)}")

    return final_audio_clip

if __name__ == "__main__":
    audio_clip = gen_audio()
    video_clip = gen_video(audio_clip)

    video_clip.write_videofile("movie.mp4", codec="libx264", audio_codec="aac")

