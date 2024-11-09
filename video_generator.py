import os
import csv
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_audioclips
from moviepy.audio.AudioClip import AudioClip
from pathlib import Path

import arabic_reshaper  # For Arabic reshaping
from bidi.algorithm import get_display  # For correct RTL display


# Literals
BRAND = 'brand'
SCENE = 'scene'
EMPTY = 'empty'

# Parameters
hours = 0.02
sec_per_hr = 3600
duration_sec = int(hours * sec_per_hr)
frames_per_sec = 3
frame_count =  duration_sec * frames_per_sec
frame_size_px = 900
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
fonts_path = os.path.join(base_path, 'fonts')

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
brand_statements_dict = {f'{b}': {} for b in brands}

################################### INITIALIZATION ###################################

def load_csv_files():
    for b in brands:
        txt_path = Path(os.path.join(brands_path, os.path.join(b, 'txt')))
        csv_files = [f for f in txt_path.iterdir() if f.is_file() and f.name.endswith('.csv')]

        if len(csv_files) == 0:
            print(f"[WARN] No CSV files found for '{b}'")
            continue

        with open(csv_files[0], mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                brand_statements_dict[b][row['language']] = row['text']

################################## VIDEO GENERATION ##################################

def add_txt_to_image(img, txt):
    try:
        font = ImageFont.truetype(os.path.join(fonts_path, "default.ttf"), 24)
    except IOError:
        print("Font file not found. Ensure you have Noto Sans with language support.")
        font = ImageFont.load_default(size=24)

    txt_color = (255, 255, 255)
    txt_background = (0 ,0 , 0)
    txt_bar_height = 50
    txt_padding_top_px = 5
    
    # Calculate txt size
    bbox = font.getbbox(txt)
    txt_width = bbox[2] - bbox[0]

    new_height = frame_size_px + txt_bar_height

    new_img = Image.new('RGB', (frame_size_px, new_height), txt_background)
    new_img.paste(img, (0, 0))

    # Draw the txt centered below the image
    draw = ImageDraw.Draw(new_img)
    txt_x = (frame_size_px - txt_width) // 2
    txt_y = frame_size_px + txt_padding_top_px

    txt = get_display(arabic_reshaper.reshape(txt))
    print(txt)
    draw.text((txt_x, txt_y), txt, fill=txt_color, font=font)

    return new_img

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
        
        # Avoid rendering a brand more than once in the same frame
        non_rendered_brands = [b for b in brands if brand_cell_indices[b][-1] == -1]

        if current_grid[i] == EMPTY:
            current_img_paths[i] = None
        elif current_grid[i] == BRAND and grid_brands_count < max_brands_per_frame and len(non_rendered_brands) > 0:
            random_brand = random.choice(non_rendered_brands)

            brand_cell_indices[random_brand].append(i)
            current_img_paths[i] = random.choice(brand_imgs[random_brand])

            grid_brands_count += 1
        else:
            current_grid[i] = SCENE
            random_scene_type = random.choice(scene_types)
            current_img_paths[i] = random.choice(scene_imgs[random_scene_type])
    
    return (current_grid, current_img_paths)

def create_frame(grid_img_paths):
    """Creates a single frame rendering the images pointed to by grid image paths."""
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

    img_txt = ' '
    if random.random() > 0.9:
        print ("Adding txt to frame")

        # Write a random brand marketing statement
        selected_brand = random.choice(brands)
        selected_lang = random.choice(list(brand_statements_dict[selected_brand].keys()))
        img_txt = brand_statements_dict[selected_brand][selected_lang]
        
    img = add_txt_to_image(img, img_txt)

    return img

def generate_video(audio):
    # Generate all frames
    frames = []
    grid = [EMPTY for _ in range(cell_count)]
    grid_img_paths = [None for _ in range(cell_count)]

    print (f"Frame count: {frame_count}")
    for i in range(frame_count):
        print (f"Frame#: {i}")
        (grid, grid_img_paths) = generate_random_grid(grid, grid_img_paths)
        frame = create_frame(grid_img_paths)

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

def generate_audio():
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
    print (f"Number of statements in audio track: {statement_count}")

    return final_audio_clip

if __name__ == "__main__":
    load_csv_files()
    audio_clip = generate_audio()
    video_clip = generate_video(audio_clip)

    video_clip.write_videofile("movie.mp4", codec="libx264", audio_codec="aac")

