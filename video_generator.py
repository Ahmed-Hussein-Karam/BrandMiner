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
cell_types_probabilities = [0.1, 0.8, 0.1]

# When a cell ttl expires, a new random ttl is set for that cell
cell_ttl = [0 for _ in range(cell_count)]

# Constants
max_cell_ttl = frames_per_sec * 2
max_enabled_brands_per_video = 5
max_imgs_per_brand = 5

# Paths
base_path = os.getcwd()
media_path = os.path.join(base_path, 'media')

brands_path = os.path.join(media_path, 'brands')
scenes_path = os.path.join(media_path, 'scenes')

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
                    cell_img = Image.open(cell_value).convert('RGBA').resize((cell_size, cell_size), Image.LANCZOS)
                    img_cache[cell_value] = cell_img

                    img.paste(cell_img, (col * cell_size, row * cell_size), cell_img)
    return img

def gen_video(audio):
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

    while curr_audio_duration_sec < duration_sec - max_silence_duration_sec + 3:
        # Append a silent clip
        audio_segments.append(create_silent_clip())
        print (f"silent clip of {audio_segments[-1].duration} sec")

        if random.random() < 0.7:
            # Append a random statement
            audio_segments.append(random_statement_audio)
            print (f"stmt clip of {audio_segments[-1].duration} sec")
        else:
            # Append a random brand audio clip
            audio_segments.append(brand_audio[random.choice(brands)])
            print (f"brand clip of {audio_segments[-1].duration} sec")
        
        curr_audio_duration_sec += audio_segments[-1].duration + audio_segments[-2].duration

    # Concatenate all audio segments
    final_audio_clip = concatenate_audioclips(audio_segments)
    print (f"Number of audio segments: {len(audio_segments)}")

    return final_audio_clip

if __name__ == "__main__":
    audio_clip = gen_audio()
    video_clip = gen_video(audio_clip)

    video_clip.write_videofile("movie.mp4", codec="libx264", audio_codec="aac")

