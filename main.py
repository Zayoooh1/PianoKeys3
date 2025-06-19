import pygame
import sys
import os
import random
import math
import threading
from mido import MidiFile, tempo2bpm, tick2second
import requests
import urllib.parse
from bs4 import BeautifulSoup


# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Custom Pygame event for thread communication
DOWNLOAD_COMPLETE_EVENT = pygame.USEREVENT + 1
# Possible statuses for the event: 'DOWNLOAD_SUCCESS', 'DOWNLOAD_ERROR_NETWORK',
# 'DOWNLOAD_ERROR_NO_MIDI_FOUND', 'PARSE_ERROR', 'SEARCH_ERROR_GENERIC', 'SUCCESS_PARSE'

# Define window dimensions
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# Create the screen surface
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

# Set window title
pygame.display.set_caption("Piano App")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)  # For shadows
LIGHTER_GRAY = (100, 100, 100) # For pressed black keys

# --- New Theme Colors ---
DARK_BACKGROUND_COLOR = (20, 20, 30)
ACCENT_COLOR_CYAN = (0, 200, 200)
ACCENT_COLOR_CYAN_BRIGHT = (min(255, ACCENT_COLOR_CYAN[0] + 40),
                              min(255, ACCENT_COLOR_CYAN[1] + 40),
                              min(255, ACCENT_COLOR_CYAN[2] + 40))
STAR_COLORS = [
    (220, 220, 255),
    (200, 200, 240),
    (255, 255, 220),
    (240, 240, 240)
]
BACKGROUND_COLOR = DARK_BACKGROUND_COLOR

# Keyboard Parameters
OCTAVES = 2
NUM_WHITE_KEYS = 7 * OCTAVES
KEYBOARD_HEIGHT_RATIO = 0.25
keyboard_height = int(WINDOW_HEIGHT * KEYBOARD_HEIGHT_RATIO)
white_key_width = WINDOW_WIDTH // NUM_WHITE_KEYS
white_key_height = keyboard_height
black_key_width = int(white_key_width * 0.6)
black_key_height = int(white_key_height * 0.6)
SHADOW_OFFSET = 3

KEYBOARD_RENDER_AREA_RECT = pygame.Rect(0, WINDOW_HEIGHT - keyboard_height, WINDOW_WIDTH, keyboard_height)


# --- Control Panel Constants ---
CONTROL_PANEL_HEIGHT = 150
CONTROL_PANEL_Y_START = WINDOW_HEIGHT - CONTROL_PANEL_HEIGHT
CONTROL_PANEL_BG_COLOR = (30, 30, 30)
BUTTON_TEXT_COLOR = (230, 230, 230)
BUTTON_BASE_COLOR = (80, 80, 80)
BUTTON_HOVER_COLOR = ACCENT_COLOR_CYAN
BUTTON_WIDTH = 100
SEARCH_BUTTON_WIDTH = 80
BUTTON_HEIGHT = 40
BUTTON_MARGIN = 10
padding = 10

SLIDER_TRACK_HEIGHT = 10
SLIDER_KNOB_WIDTH = 15
SLIDER_KNOB_HEIGHT = 30
SLIDER_WIDTH = 150
PROGRESS_BAR_HEIGHT = 15

# Search UI Constants
SEARCH_INPUT_WIDTH = 200
SEARCH_INPUT_HEIGHT = BUTTON_HEIGHT


try:
    control_panel_font = pygame.font.Font(None, 28)
except Exception as e:
    print(f"Could not load default font for control panel, using fallback pygame.font.SysFont: {e}")
    control_panel_font = pygame.font.SysFont(pygame.font.get_default_font(), 28)

# --- UI Element Definitions ---
search_button_props_dict = {
    'rect': None,
    'text': "Search", 'action_id': 'action_search_midi',
    'base_color': BUTTON_BASE_COLOR, 'hover_color': BUTTON_HOVER_COLOR,
    'text_color': BUTTON_TEXT_COLOR, 'font': control_panel_font,
    'width': SEARCH_BUTTON_WIDTH
}

control_panel_buttons = []
main_button_actions = ['action_start', 'action_pause', 'action_stop', 'action_toggle_mode']
main_button_texts = ["Start", "Pause", "Stop", "Mode: Learning"]

for i, action in enumerate(main_button_actions):
    btn_rect = pygame.Rect(0, 0, BUTTON_WIDTH, BUTTON_HEIGHT)
    control_panel_buttons.append({
        'rect': btn_rect, 'text': main_button_texts[i], 'action_id': action,
        'base_color': BUTTON_BASE_COLOR, 'hover_color': BUTTON_HOVER_COLOR,
        'text_color': BUTTON_TEXT_COLOR, 'font': control_panel_font,
        'width': BUTTON_WIDTH
    })

tempo_slider_props = {
    'label': "Tempo", 'value_range': (0.5, 2.0),
    'current_value_func': lambda: tempo_multiplier, 'setter_func': None,
    'rect': None, 'knob_rect': None,
    'text_label_func': lambda: f"Tempo: {int(base_bpm * tempo_multiplier)} BPM"
}
volume_slider_props = {
    'label': "Volume", 'value_range': (0.0, 1.0),
    'current_value_func': lambda: global_volume, 'setter_func': None,
    'rect': None, 'knob_rect': None,
    'text_label_func': lambda: f"Volume: {int(global_volume * 100)}%"
}
sliders_list = [tempo_slider_props, volume_slider_props]
progress_bar_props = {
    'rect': None, 'fill_color': PROGRESS_BAR_FILL_COLOR,
    'track_color': PROGRESS_BAR_TRACK_COLOR
}

NUM_STARS = 100; stars = []
max_y_for_stars = WINDOW_HEIGHT - CONTROL_PANEL_HEIGHT
if max_y_for_stars <=0: max_y_for_stars = WINDOW_HEIGHT
for _ in range(NUM_STARS):
    stars.append({'x': random.randint(0, WINDOW_WIDTH), 'y': random.randint(0, max_y_for_stars),
                  'radius': random.uniform(0.5, 1.5),'base_color_tuple': random.choice(STAR_COLORS),
                  'current_alpha': 0.0, 'alpha_cycle_duration': random.uniform(2000, 5000),
                  'alpha_cycle_time': random.uniform(0, 5000)})
active_shockwaves = []
last_drawn_white_key_rects = []; last_drawn_black_key_rects = []
PIANO_ROLL_LOOKAHEAD_SECONDS = 5.0; PIANO_ROLL_SECONDS_ON_SCREEN = 5.0
PIANO_ROLL_TOP_Y = 50; PIANO_ROLL_BOTTOM_Y = WINDOW_HEIGHT - keyboard_height - 10
NOTE_RECT_COLOR = ACCENT_COLOR_CYAN; NOTE_RECT_BORDER_COLOR = (100, 220, 220)
NOTE_RECT_WIDTH_WHITE_RATIO = 0.8; NOTE_RECT_WIDTH_BLACK_RATIO = 0.9
if PIANO_ROLL_BOTTOM_Y > PIANO_ROLL_TOP_Y and PIANO_ROLL_SECONDS_ON_SCREEN > 0:
    pixels_per_second = (PIANO_ROLL_BOTTOM_Y - PIANO_ROLL_TOP_Y) / PIANO_ROLL_SECONDS_ON_SCREEN
else:
    pixels_per_second = 0; print("Warning: Piano roll Y coordinates or seconds_on_screen are configured incorrectly.")
NUM_BLACK_KEYS = 5 * OCTAVES
white_key_pressed_states = [False] * NUM_WHITE_KEYS; black_key_pressed_states = [False] * NUM_BLACK_KEYS
SOUNDS_DIR = "downloads";
PLACEHOLDER_SOUND = os.path.join(SOUNDS_DIR, "placeholder.wav")
CORRECT_SOUND_FILE = os.path.join(SOUNDS_DIR, "correct.wav"); INCORRECT_SOUND_FILE = os.path.join(SOUNDS_DIR, "incorrect.wav")
correct_sound = None; incorrect_sound = None
try: correct_sound = pygame.mixer.Sound(CORRECT_SOUND_FILE)
except pygame.error as e: print(f"Could not load correct sound {CORRECT_SOUND_FILE}: {e}.")
try: incorrect_sound = pygame.mixer.Sound(INCORRECT_SOUND_FILE)
except pygame.error as e: print(f"Could not load incorrect sound {INCORRECT_SOUND_FILE}: {e}.")
if not os.path.exists(SOUNDS_DIR): os.makedirs(SOUNDS_DIR)
if not os.path.exists(CORRECT_SOUND_FILE) and SOUNDS_DIR in CORRECT_SOUND_FILE : open(CORRECT_SOUND_FILE, 'w').close()
if not os.path.exists(INCORRECT_SOUND_FILE) and SOUNDS_DIR in INCORRECT_SOUND_FILE: open(INCORRECT_SOUND_FILE, 'w').close()

key_map = { pygame.K_a: {'type': 'white', 'index': 0, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_s: {'type': 'white', 'index': 1, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_d: {'type': 'white', 'index': 2, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_f: {'type': 'white', 'index': 3, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_g: {'type': 'white', 'index': 4, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_h: {'type': 'white', 'index': 5, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_j: {'type': 'white', 'index': 6, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_k: {'type': 'white', 'index': 7, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_l: {'type': 'white', 'index': 8, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_SEMICOLON: {'type': 'white', 'index': 9, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_w: {'type': 'black', 'index': 0, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_e: {'type': 'black', 'index': 1, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_t: {'type': 'black', 'index': 2, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_y: {'type': 'black', 'index': 3, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_u: {'type': 'black', 'index': 4, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_o: {'type': 'black', 'index': 5, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}, pygame.K_p: {'type': 'black', 'index': 6, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None}}
for key_code, data in key_map.items():
    if SOUNDS_DIR in data['sound_file'] and not os.path.exists(data['sound_file']): open(data['sound_file'],'w').close()
    try: data['sound_obj'] = pygame.mixer.Sound(data['sound_file'])
    except pygame.error as e: print(f"Could not load sound for key {pygame.key.name(key_code)}: {data['sound_file']} - {e}")

midi_to_sound_map = {}; KEYBOARD_START_MIDI_NOTE = 60
WHITE_KEY_MIDI_OFFSETS = [0, 2, 4, 5, 7, 9, 11]; BLACK_KEY_MIDI_OFFSETS = [1, 3, 6, 8, 10]
for pc_key, data in key_map.items():
    key_type = data['type']; key_index_on_keyboard = data['index']; sound_obj = data['sound_obj']
    if sound_obj:
        midi_note = -1
        if key_type == 'white': octave_num = (KEYBOARD_START_MIDI_NOTE // 12) + (key_index_on_keyboard // 7); offset_in_octave = WHITE_KEY_MIDI_OFFSETS[key_index_on_keyboard % 7]; midi_note = octave_num * 12 + offset_in_octave
        elif key_type == 'black': octave_num = (KEYBOARD_START_MIDI_NOTE // 12) + (key_index_on_keyboard // 5); offset_in_octave = BLACK_KEY_MIDI_OFFSETS[key_index_on_keyboard % 5]; midi_note = octave_num * 12 + offset_in_octave
        if midi_note != -1 and midi_note not in midi_to_sound_map: midi_to_sound_map[midi_note] = sound_obj
pc_key_to_midi_map = {}
for pc_key_code, data in key_map.items():
    key_type = data['type']; key_index_in_type = data['index']; midi_note = -1
    if key_type == 'white': octave_num_for_key = (KEYBOARD_START_MIDI_NOTE // 12) + (key_index_in_type // 7); offset_in_octave_for_key = WHITE_KEY_MIDI_OFFSETS[key_index_in_type % 7]; midi_note = octave_num_for_key * 12 + offset_in_octave_for_key
    elif key_type == 'black': octave_num_for_key = (KEYBOARD_START_MIDI_NOTE // 12) + (key_index_in_type // 5); offset_in_octave_for_key = BLACK_KEY_MIDI_OFFSETS[key_index_in_type % 5]; midi_note = octave_num_for_key * 12 + offset_in_octave_for_key
    if midi_note != -1: pc_key_to_midi_map[pc_key_code] = midi_note
song_data = [{'midi_note': 67, 'start_time': 0.0, 'duration': 0.4, 'played': False}, {'midi_note': 64, 'start_time': 0.5, 'duration': 0.4, 'played': False}, {'midi_note': 60, 'start_time': 1.0, 'duration': 0.4, 'played': False},{'midi_note': 67, 'start_time': 1.5, 'duration': 0.4, 'played': False},{'midi_note': 69, 'start_time': 2.0, 'duration': 0.4, 'played': False},{'midi_note': 67, 'start_time': 2.5, 'duration': 0.4, 'played': False},{'midi_note': 64, 'start_time': 3.0, 'duration': 0.4, 'played': False},{'midi_note': 60, 'start_time': 3.5, 'duration': 0.4, 'played': False},{'midi_note': 67, 'start_time': 4.0, 'duration': 0.4, 'played': False}]
total_song_duration_seconds = 0.0
def get_total_song_duration(notes_list):
    if not notes_list: return 0.0
    max_end_time = 0.0
    for note in notes_list: note_end_time = note.get('start_time', 0) + note.get('duration', 0); max_end_time = max(max_end_time, note_end_time)
    return max_end_time
total_song_duration_seconds = get_total_song_duration(song_data)
APP_MODES = {'LEARNING': 0, 'PRESENTATION': 1}; current_mode = APP_MODES['LEARNING']
learning_mode_state = {'paused_at_time': None, 'notes_at_pause': [], 'correctly_pressed_midi_in_pause': set()}
feedback_flash_info = {'key_midi': None, 'color': None, 'end_time_ms': 0}
base_bpm = 120.0; tempo_multiplier = 1.0; global_volume = 1.0
dragging_tempo_slider = False; dragging_volume_slider = False
song_playback_status = 'STOPPED'; mode_switch_confirm_active = False; target_mode_on_confirm = None; time_paused_at_ticks = 0
current_song_time_seconds = 0.0; song_time_at_last_event = 0.0; real_ticks_at_last_event = 0
search_input_text = ""; search_input_active = False; search_input_field_rect = pygame.Rect(0,0,0,0)
search_status = 'IDLE'; search_feedback_message = ""
def reset_song_played_states(notes_list):
    for note_info in notes_list: note_info['played'] = False
def reset_learning_mode_specific_states():
    global learning_mode_state
    learning_mode_state['paused_at_time'] = None; learning_mode_state['notes_at_pause'].clear(); learning_mode_state['correctly_pressed_midi_in_pause'].clear()
def set_global_application_volume(volume_level):
    clamped_volume = max(0.0, min(1.0, volume_level))
    for pc_key_data in key_map.values():
        if pc_key_data['sound_obj']: pc_key_data['sound_obj'].set_volume(clamped_volume)
    for sound_obj in midi_to_sound_map.values():
        if sound_obj: sound_obj.set_volume(clamped_volume)
    if correct_sound: correct_sound.set_volume(clamped_volume)
    if incorrect_sound: incorrect_sound.set_volume(clamped_volume)

def sanitize_filename(name_str):
    name_str = name_str.strip().replace(' ', '_')
    valid_chars = "-_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    sanitized_name = "".join(c if c in valid_chars else '_' for c in name_str)
    if not sanitized_name or sanitized_name.strip("._") == "": sanitized_name = "downloaded_midi"
    return sanitized_name[:100]

def _download_and_save_file_thread(midi_url_str, http_headers, original_song_title_str):
    try:
        midi_response = requests.get(midi_url_str, headers=http_headers, stream=True, timeout=20)
        midi_response.raise_for_status()
        base_filename = sanitize_filename(original_song_title_str)
        downloads_dir = "downloads"
        if not os.path.exists(downloads_dir): os.makedirs(downloads_dir)
        filename = os.path.join(downloads_dir, f"{base_filename}.mid")
        with open(filename, 'wb') as f:
            for chunk in midi_response.iter_content(chunk_size=8192): f.write(chunk)
        pygame.event.post(pygame.event.Event(DOWNLOAD_COMPLETE_EVENT, {'status': 'DOWNLOAD_SUCCESS', 'message': f"Downloaded: {os.path.basename(filename)}", 'filepath': os.path.abspath(filename)}))
    except Exception as e:
        pygame.event.post(pygame.event.Event(DOWNLOAD_COMPLETE_EVENT, {'status': 'DOWNLOAD_ERROR_NETWORK', 'message': f"Download failed: {e}", 'filepath': None}))

def _find_midi_on_song_page_thread(song_page_url_str, http_headers, original_song_title):
    try:
        song_page_response = requests.get(song_page_url_str, headers=http_headers, timeout=10)
        song_page_response.raise_for_status()
        song_soup = BeautifulSoup(song_page_response.text, 'html.parser')
        midi_download_url = None
        all_links_on_song_page = song_soup.find_all('a', href=True)
        for link_tag in all_links_on_song_page:
            if link_tag['href'].lower().endswith('.mid'): midi_download_url = link_tag['href']; break
        if not midi_download_url:
            possible_download_texts = ["download midi", "download .mid", "get midi"]
            for link_tag in all_links_on_song_page:
                if any(text in link_tag.text.lower() for text in possible_download_texts): midi_download_url = link_tag['href']; break
        if not midi_download_url:
            dl_button = song_soup.find('a', id='downloadLink') or song_soup.find('a', class_='btn-download-midi') or song_soup.find('input', type='submit', value='Download')
            if dl_button and dl_button.get('href'): midi_download_url = dl_button['href']
        if midi_download_url:
            midi_download_url = urllib.parse.urljoin(song_page_url_str, midi_download_url)
            _download_and_save_file_thread(midi_download_url, http_headers, original_song_title)
        else: pygame.event.post(pygame.event.Event(DOWNLOAD_COMPLETE_EVENT, {'status': 'DOWNLOAD_ERROR_NO_MIDI_FOUND', 'message': "No MIDI link on song page.",'filepath': None}))
    except Exception as e:
        pygame.event.post(pygame.event.Event(DOWNLOAD_COMPLETE_EVENT, {'status': 'DOWNLOAD_ERROR_NETWORK', 'message': f"Song page error: {e}",'filepath': None}))

def downloader_thread_target(song_title_for_download):
    search_query = urllib.parse.quote_plus(song_title_for_download)
    search_url = f"https://freemidi.org/search?query={search_query}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        found_link_tag = None
        results_container = soup.find('div', class_='results-list')
        if results_container:
            links_in_container = results_container.find_all('a', href=True)
            for link in links_in_container:
                if song_title_for_download.lower().split() and song_title_for_download.lower().split()[0] in link.text.lower():
                    found_link_tag = link; break
        if not found_link_tag:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                if song_title_for_download.lower() in link.text.lower():
                    href = link['href']
                    if not any(x in href for x in ['/genre-', '/artist-', 'javascript:', '#']):
                        found_link_tag = link; break
        if found_link_tag:
            relative_url = found_link_tag['href']
            song_page_url = urllib.parse.urljoin(search_url, relative_url)
            _find_midi_on_song_page_thread(song_page_url, headers, song_title_for_download)
        else: pygame.event.post(pygame.event.Event(DOWNLOAD_COMPLETE_EVENT, {'status': 'DOWNLOAD_ERROR_NO_MIDI_FOUND', 'message': "Song not found in search.", 'filepath': None}))
    except Exception as e:
        pygame.event.post(pygame.event.Event(DOWNLOAD_COMPLETE_EVENT, {'status': 'SEARCH_ERROR_GENERIC', 'message': f"Search failed: {e}",'filepath': None}))

def parse_midi_to_song_data(filepath):
    global song_data, total_song_duration_seconds, song_playback_status
    global current_song_time_seconds, song_time_at_last_event, real_ticks_at_last_event
    try:
        print(f"Parsing MIDI file: {filepath}")
        mid = MidiFile(filepath)
        new_song_notes = []
        open_notes = {}
        current_time_abs = 0.0
        current_tempo = 500000
        ticks_per_beat = mid.ticks_per_beat if mid.ticks_per_beat else 480
        if not mid.ticks_per_beat: print("Warning: MIDI file has no ticks_per_beat. Assuming 480.")

        track_to_iterate = []
        if hasattr(mid, 'merged_track'): track_to_iterate = mid.merged_track
        elif mid.tracks: track_to_iterate = mid.tracks[0]
        else: raise ValueError("MIDI file contains no tracks.")

        for msg in track_to_iterate:
            current_time_abs += tick2second(msg.time, ticks_per_beat, current_tempo)
            if msg.is_meta and msg.type == 'set_tempo': current_tempo = msg.tempo
            elif msg.type == 'note_on' and msg.velocity > 0: open_notes[msg.note] = current_time_abs
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                if msg.note in open_notes:
                    start_time = open_notes.pop(msg.note)
                    duration = current_time_abs - start_time
                    if duration <= 0.01: duration = tick2second(ticks_per_beat / 8, ticks_per_beat, current_tempo);
                    if duration <= 0.01: duration = 0.05
                    new_song_notes.append({'midi_note': msg.note, 'start_time': start_time, 'duration': duration, 'played': False})

        if not new_song_notes:
            pygame.event.post(pygame.event.Event(DOWNLOAD_COMPLETE_EVENT, {'status': 'PARSE_ERROR', 'message': "No notes found in MIDI.", 'filepath': filepath})); return
        new_song_notes.sort(key=lambda x: x['start_time'])
        song_data = new_song_notes
        total_song_duration_seconds = get_total_song_duration(song_data)
        song_playback_status = 'STOPPED'; current_song_time_seconds = 0.0
        song_time_at_last_event = 0.0; real_ticks_at_last_event = 0
        reset_learning_mode_specific_states()
        pygame.event.post(pygame.event.Event(DOWNLOAD_COMPLETE_EVENT, {'status': 'SUCCESS_PARSE', 'message': f"Loaded: {os.path.basename(filepath)} ({len(song_data)} notes). Press Start.", 'filepath': filepath}))
        print(f"Successfully parsed MIDI. {len(song_data)} notes loaded.")
    except ValueError as ve:
        print(f"MIDI parsing error for {filepath}: {ve}")
        pygame.event.post(pygame.event.Event(DOWNLOAD_COMPLETE_EVENT, {'status': 'PARSE_ERROR', 'message': f"MIDI format error: {ve}", 'filepath': filepath}))
    except Exception as e:
        print(f"Error parsing MIDI file {filepath}: {e}")
        pygame.event.post(pygame.event.Event(DOWNLOAD_COMPLETE_EVENT, {'status': 'PARSE_ERROR', 'message': f"Error parsing: {e}", 'filepath': filepath}))

song_playback_status = 'STOPPED'; current_song_time_seconds = 0.0; song_time_at_last_event = 0.0; real_ticks_at_last_event = 0
reset_song_played_states(song_data); reset_learning_mode_specific_states(); set_global_application_volume(global_volume)
def get_x_for_midi_note(midi_note, first_midi_note_on_keyboard, num_total_white_keys, white_key_width_px):
    white_note_positions_in_octave = [0, 2, 4, 5, 7, 9, 11]; semitone = midi_note % 12; octave = midi_note // 12
    white_key_map = {0:0, 1:0, 2:1, 3:1, 4:2, 5:3, 6:3, 7:4, 8:4, 9:5, 10:5, 11:6}
    white_key_num_in_octave = white_key_map[semitone]; base_octave = first_midi_note_on_keyboard // 12
    total_white_key_index = (octave - base_octave) * 7 + white_key_num_in_octave
    if not (0 <= total_white_key_index < num_total_white_keys): return None
    return (total_white_key_index + 1) * white_key_width_px if semitone not in white_note_positions_in_octave else (total_white_key_index * white_key_width_px) + (white_key_width_px / 2.0)
def get_key_type_and_index_for_midi(midi_note, first_midi_note_on_keyboard, num_total_white_keys, num_total_black_keys):
    semitone = midi_note % 12; octave = midi_note // 12; base_octave = first_midi_note_on_keyboard // 12
    white_note_semitones_in_octave = [0, 2, 4, 5, 7, 9, 11]
    white_key_indices_map = {0:0, 1:0, 2:1, 3:1, 4:2, 5:3, 6:3, 7:4, 8:4, 9:5, 10:5, 11:6}
    black_key_indices_map = {1:0, 3:1, 6:2, 8:3, 10:4}
    key_type, key_index = None, None
    if semitone in white_note_semitones_in_octave:
        key_type = 'white'; idx_in_octave = white_key_indices_map[semitone]; key_index = (octave - base_octave) * 7 + idx_in_octave
        if not (0 <= key_index < num_total_white_keys): return None, None
    elif semitone in black_key_indices_map:
        key_type = 'black'; idx_in_octave = black_key_indices_map[semitone]; key_index = (octave - base_octave) * 5 + idx_in_octave
        if not (0 <= key_index < num_total_black_keys): return None, None
    else: return None, None
    return key_type, key_index
def get_rect_for_midi_note(midi_note):
    key_type, key_idx = get_key_type_and_index_for_midi(midi_note, KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, NUM_BLACK_KEYS)
    if key_type == 'white' and 0 <= key_idx < len(last_drawn_white_key_rects): return last_drawn_white_key_rects[key_idx]
    elif key_type == 'black' and 0 <= key_idx < len(last_drawn_black_key_rects): return last_drawn_black_key_rects[key_idx]
    return None
def update_stars(star_list_ref, dt_ms):
    for star in star_list_ref:
        star['alpha_cycle_time'] = (star['alpha_cycle_time'] + dt_ms) % star['alpha_cycle_duration']
        normalized_time = star['alpha_cycle_time'] / star['alpha_cycle_duration']
        star['current_alpha'] = 0.5 * (1 + math.sin(normalized_time * math.pi * 2))
def draw_stars(surface, star_list_ref):
    for star in star_list_ref:
        base_r, base_g, base_b = star['base_color_tuple']
        alpha_factor = star['current_alpha']
        final_r = int(base_r * alpha_factor); final_g = int(base_g * alpha_factor); final_b = int(base_b * alpha_factor)
        final_color = (max(0, min(255, final_r)), max(0, min(255, final_g)), max(0, min(255, final_b)))
        if star['radius'] >= 1: pygame.draw.circle(surface, final_color, (star['x'], star['y']), int(star['radius']))
        elif alpha_factor > 0.5 : surface.set_at((star['x'], star['y']), final_color)
def manage_shockwaves(surface, shockwave_list_ref, current_ticks_ref, clip_area_rect):
    num_rings = 3; ring_base_thickness = 4
    for i in range(len(shockwave_list_ref) - 1, -1, -1):
        sw = shockwave_list_ref[i]; elapsed_ms = current_ticks_ref - sw['start_time_ms']
        if elapsed_ms > sw['duration_ms']: shockwave_list_ref.pop(i); continue
        progress_ratio = elapsed_ms / sw['duration_ms']
        current_max_ring_radius = sw['max_radius'] * progress_ratio
        alpha_value = int(max(0, min(255, 255 * (1.0 - progress_ratio**2))))
        original_clip = surface.get_clip(); surface.set_clip(clip_area_rect)
        for ring_idx in range(num_rings):
            ring_radius = current_max_ring_radius * (1 - (ring_idx / num_rings) * 0.7)
            if ring_radius < 1: continue
            thickness = max(1, int(ring_base_thickness * (1.0 - progress_ratio)))
            r, g, b = sw['color']; alpha_factor = alpha_value / 255.0
            current_ring_color_tuple = (int(r * alpha_factor), int(g * alpha_factor), int(b * alpha_factor))
            current_ring_color_clamped = (max(0,min(255,c)) for c in current_ring_color_tuple)
            try: pygame.draw.circle(surface, tuple(current_ring_color_clamped), (sw['center_x'], sw['center_y']), int(ring_radius), thickness)
            except pygame.error: pass
        surface.set_clip(original_clip)
def draw_piano_roll_notes(surface, current_time_sec, notes_list, px_per_sec, lookahead_sec, first_midi_ref, total_white_keys_ref, white_key_w_ref, black_key_w_ref):
    if px_per_sec <= 0: return
    for note in notes_list:
        note_end_time = note['start_time'] + note['duration']
        if note['start_time'] < current_time_sec + lookahead_sec and note_end_time > current_time_sec:
            x_center = get_x_for_midi_note(note['midi_note'], first_midi_ref, total_white_keys_ref, white_key_w_ref)
            if x_center is None: continue
            semitone = note['midi_note'] % 12; white_note_semitones = [0, 2, 4, 5, 7, 9, 11]; is_white_note = semitone in white_note_semitones
            rect_width = white_key_w_ref * NOTE_RECT_WIDTH_WHITE_RATIO if is_white_note else black_key_w_ref * NOTE_RECT_WIDTH_BLACK_RATIO
            rect_left_x = x_center - (rect_width / 2)
            time_offset_sec = note['start_time'] - current_time_sec; y_offset_px = time_offset_sec * px_per_sec
            note_bottom_y_on_roll = PIANO_ROLL_BOTTOM_Y - y_offset_px; note_height_px = note['duration'] * px_per_sec
            note_top_y_on_roll = note_bottom_y_on_roll - note_height_px
            visible_top_y = max(note_top_y_on_roll, PIANO_ROLL_TOP_Y); visible_bottom_y = min(note_bottom_y_on_roll, PIANO_ROLL_BOTTOM_Y)
            visible_height = visible_bottom_y - visible_top_y
            if visible_height > 0:
                note_rect = pygame.Rect(rect_left_x, visible_top_y, rect_width, visible_height)
                pygame.draw.rect(surface, NOTE_RECT_COLOR, note_rect); pygame.draw.rect(surface, NOTE_RECT_BORDER_COLOR, note_rect, 1)
def draw_control_panel(surface, buttons_list_ref, sliders_list_ref, progress_bar_props_ref, current_app_mode_val, app_modes_ref, mouse_pos_tuple, current_song_time_ref, total_song_duration_ref, base_bpm_ref, is_dragging_tempo, is_dragging_volume, current_search_input_text, is_search_input_active, current_search_feedback_msg):
    global search_input_field_rect
    panel_rect_bg = pygame.Rect(0, CONTROL_PANEL_Y_START, WINDOW_WIDTH, CONTROL_PANEL_HEIGHT); pygame.draw.rect(surface, CONTROL_PANEL_BG_COLOR, panel_rect_bg)
    padding_cp = 10; slider_label_width_cp = 150; slider_y_pos_abs_cp = CONTROL_PANEL_Y_START + padding_cp; slider_track_width_actual_cp = SLIDER_WIDTH
    tempo_slider = sliders_list_ref[0]; tempo_label_x_start_cp = padding_cp ; tempo_slider_track_x_start_cp = tempo_label_x_start_cp + slider_label_width_cp + padding_cp
    tempo_slider['rect'] = pygame.Rect(tempo_slider_track_x_start_cp, slider_y_pos_abs_cp + (SLIDER_KNOB_HEIGHT - SLIDER_TRACK_HEIGHT)//2, slider_track_width_actual_cp, SLIDER_TRACK_HEIGHT)
    tempo_text = tempo_slider['text_label_func'](); tempo_label_surf = control_panel_font.render(tempo_text, True, BUTTON_TEXT_COLOR); tempo_label_rect = tempo_label_surf.get_rect(left=tempo_label_x_start_cp, centery=tempo_slider['rect'].centery); surface.blit(tempo_label_surf, tempo_label_rect)
    pygame.draw.rect(surface, SLIDER_TRACK_COLOR, tempo_slider['rect'], border_radius=5); tempo_val = tempo_slider['current_value_func'](); tempo_min, tempo_max = tempo_slider['value_range']
    knob_x_ratio_tempo = (tempo_val - tempo_min) / (tempo_max - tempo_min) if (tempo_max - tempo_min) != 0 else 0; knob_x_tempo = tempo_slider['rect'].left + int(knob_x_ratio_tempo * tempo_slider['rect'].width)
    tempo_slider['knob_rect'] = pygame.Rect(knob_x_tempo - SLIDER_KNOB_WIDTH // 2, slider_y_pos_abs_cp, SLIDER_KNOB_WIDTH, SLIDER_KNOB_HEIGHT)
    tempo_knob_color_to_use = ACCENT_COLOR_CYAN_BRIGHT if is_dragging_tempo else SLIDER_KNOB_COLOR
    pygame.draw.rect(surface, tempo_knob_color_to_use, tempo_slider['knob_rect'], border_radius=3)
    volume_slider = sliders_list_ref[1]; volume_label_x_start_cp = tempo_slider_track_x_start_cp + slider_track_width_actual_cp + padding_cp * 2; volume_slider_track_x_start_cp = volume_label_x_start_cp + slider_label_width_cp + padding_cp
    volume_slider['rect'] = pygame.Rect(volume_slider_track_x_start_cp, slider_y_pos_abs_cp + (SLIDER_KNOB_HEIGHT - SLIDER_TRACK_HEIGHT)//2, slider_track_width_actual_cp, SLIDER_TRACK_HEIGHT)
    volume_text = volume_slider['text_label_func'](); volume_label_surf = control_panel_font.render(volume_text, True, BUTTON_TEXT_COLOR); volume_label_rect = volume_label_surf.get_rect(left=volume_label_x_start_cp, centery=volume_slider['rect'].centery); surface.blit(volume_label_surf, volume_label_rect)
    pygame.draw.rect(surface, SLIDER_TRACK_COLOR, volume_slider['rect'], border_radius=5); volume_val = volume_slider['current_value_func'](); volume_min, volume_max = volume_slider['value_range']
    knob_x_ratio_volume = (volume_val - volume_min) / (volume_max - volume_min) if (volume_max - volume_min) != 0 else 0; knob_x_volume = volume_slider['rect'].left + int(knob_x_ratio_volume * volume_slider['rect'].width)
    volume_slider['knob_rect'] = pygame.Rect(knob_x_volume - SLIDER_KNOB_WIDTH // 2, slider_y_pos_abs_cp, SLIDER_KNOB_WIDTH, SLIDER_KNOB_HEIGHT)
    volume_knob_color_to_use = ACCENT_COLOR_CYAN_BRIGHT if is_dragging_volume else SLIDER_KNOB_COLOR
    pygame.draw.rect(surface, volume_knob_color_to_use, volume_slider['knob_rect'], border_radius=3)
    progress_bar_y_pos_abs_cp = slider_y_pos_abs_cp + SLIDER_KNOB_HEIGHT + padding_cp; progress_bar_width_actual_cp = WINDOW_WIDTH - 2 * padding_cp
    progress_bar_props_ref['rect'] = pygame.Rect(padding_cp, progress_bar_y_pos_abs_cp, progress_bar_width_actual_cp, PROGRESS_BAR_HEIGHT); pygame.draw.rect(surface, progress_bar_props_ref['track_color'], progress_bar_props_ref['rect'], border_radius=3)
    if total_song_duration_ref > 0:
        progress_ratio = min(current_song_time_ref / total_song_duration_ref, 1.0) if total_song_duration_ref > 0 else 0; fill_width = int(progress_ratio * progress_bar_props_ref['rect'].width)
        if fill_width > 0: fill_rect = pygame.Rect(progress_bar_props_ref['rect'].left, progress_bar_props_ref['rect'].top, fill_width, progress_bar_props_ref['rect'].height); pygame.draw.rect(surface, progress_bar_props_ref['fill_color'], fill_rect, border_radius=3)
    search_ui_y_abs_cp = progress_bar_y_pos_abs_cp + PROGRESS_BAR_HEIGHT + padding_cp
    search_input_field_rect.topleft = (padding_cp, search_ui_y_abs_cp); search_input_field_rect.size = (SEARCH_INPUT_WIDTH, SEARCH_INPUT_HEIGHT)
    pygame.draw.rect(surface, (60, 60, 70) if is_search_input_active else (40, 40, 50), search_input_field_rect)
    pygame.draw.rect(surface, ACCENT_COLOR_CYAN if is_search_input_active else (80,80,80), search_input_field_rect, 1)
    text_surface_search = control_panel_font.render(current_search_input_text + ('|' if is_search_input_active and int(pygame.time.get_ticks() / 500) % 2 == 0 else ''), True, BUTTON_TEXT_COLOR)
    surface.blit(text_surface_search, (search_input_field_rect.x + 5, search_input_field_rect.y + (search_input_field_rect.height - text_surface_search.get_height()) // 2))
    all_buttons_for_layout_cp = [search_button_props_dict] + buttons_list_ref
    current_x_offset_cp = padding_cp + SEARCH_INPUT_WIDTH + BUTTON_MARGIN
    search_button_props_dict['rect'] = pygame.Rect(current_x_offset_cp, search_ui_y_abs_cp, search_button_props_dict['width'], BUTTON_HEIGHT)
    current_x_offset_cp += search_button_props_dict['width'] + BUTTON_MARGIN * 2
    remaining_width_for_main_buttons = WINDOW_WIDTH - current_x_offset_cp - padding_cp
    num_main_buttons = len(buttons_list_ref); total_main_buttons_width = num_main_buttons * BUTTON_WIDTH + (num_main_buttons - 1) * BUTTON_MARGIN
    start_x_main_buttons = current_x_offset_cp + (remaining_width_for_main_buttons - total_main_buttons_width) // 2
    if start_x_main_buttons < current_x_offset_cp : start_x_main_buttons = current_x_offset_cp
    for i, button_info in enumerate(buttons_list_ref): button_info['rect'].topleft = (start_x_main_buttons + i * (BUTTON_WIDTH + BUTTON_MARGIN), search_ui_y_abs_cp)
    for button_info in all_buttons_for_layout_cp:
        btn_rect_updated = button_info['rect']; current_btn_color = button_info['base_color']; is_hovered = btn_rect_updated.collidepoint(mouse_pos_tuple)
        if button_info['action_id'] == 'action_toggle_mode':
            current_btn_color = ACCENT_COLOR_CYAN
            if is_hovered: r, g, b = ACCENT_COLOR_CYAN; hover_brightness_increase = 30; current_btn_color = (min(255, r + hover_brightness_increase), min(255, g + hover_brightness_increase), min(255, b + hover_brightness_increase))
        elif is_hovered: current_btn_color = button_info['hover_color']
        pygame.draw.rect(surface, current_btn_color, btn_rect_updated); pygame.draw.rect(surface, (50,50,50), btn_rect_updated, 1)
        button_text_content = button_info['text']
        if button_info['action_id'] == 'action_toggle_mode': mode_name = "Learning" if current_app_mode_val == app_modes_ref['LEARNING'] else "Presentation"; button_text_content = f"Mode: {mode_name}"
        if button_info['font'] and button_text_content: text_surf = button_info['font'].render(button_text_content, True, button_info['text_color']); text_rect = text_surf.get_rect(center=btn_rect_updated.center); surface.blit(text_surf, text_rect)
    if current_search_feedback_msg:
        feedback_surf = control_panel_font.render(current_search_feedback_msg, True, ACCENT_COLOR_CYAN)
        feedback_rect = feedback_surf.get_rect(centerx=WINDOW_WIDTH / 2, bottom=CONTROL_PANEL_Y_START - 5)
        if feedback_rect.bottom > 0 and feedback_rect.top < WINDOW_HEIGHT : surface.blit(feedback_surf, feedback_rect)
def draw_feedback_flash_overlay(surface, flash_info, first_midi_ref, num_white_keys_ref, num_black_keys_ref, white_key_w_ref, keyboard_y_start_ref, white_key_h_ref, black_key_w_ref, black_key_h_ref):
    if flash_info['key_midi'] is None or flash_info['end_time_ms'] <= pygame.time.get_ticks(): flash_info['key_midi'] = None; return
    key_type, key_idx = get_key_type_and_index_for_midi(flash_info['key_midi'],first_midi_ref,num_white_keys_ref,num_black_keys_ref)
    if key_type is None: flash_info['key_midi'] = None; return
    flash_rect = None; key_center_x = get_x_for_midi_note(flash_info['key_midi'], first_midi_ref, num_white_keys_ref, white_key_w_ref)
    if key_center_x is None: flash_info['key_midi'] = None; return
    current_key_width = white_key_w_ref if key_type == 'white' else black_key_w_ref; current_key_height = white_key_h_ref if key_type == 'white' else black_key_h_ref
    key_top_left_x = key_center_x - (current_key_width / 2)
    flash_rect = pygame.Rect(key_top_left_x, keyboard_y_start_ref, current_key_width, current_key_height)
    if flash_rect: flash_surface = pygame.Surface(flash_rect.size, pygame.SRCALPHA); flash_surface.fill((*flash_info['color'], 128)); surface.blit(flash_surface, flash_rect.topleft)
    else: flash_info['key_midi'] = None
def draw_white_key(surface, rect, shadow_offset, is_pressed):
    current_fill_color = GRAY if is_pressed else WHITE
    if is_pressed: pygame.draw.rect(surface, current_fill_color, rect); pygame.draw.rect(surface, BLACK, rect, 1)
    else: shadow_rect = rect.move(shadow_offset, shadow_offset); pygame.draw.rect(surface, GRAY, shadow_rect); pygame.draw.rect(surface, current_fill_color, rect); pygame.draw.rect(surface, BLACK, rect, 2)
def draw_black_key(surface, rect, shadow_offset, is_pressed):
    current_fill_color = LIGHTER_GRAY if is_pressed else BLACK
    if is_pressed: pygame.draw.rect(surface, current_fill_color, rect)
    else: shadow_rect = rect.move(shadow_offset, shadow_offset); pygame.draw.rect(surface, (150,150,150), shadow_rect) ; pygame.draw.rect(surface, current_fill_color, rect)
def draw_piano(surface, white_pressed_states, black_pressed_states):
    global last_drawn_white_key_rects, last_drawn_black_key_rects
    last_drawn_white_key_rects.clear(); last_drawn_black_key_rects.clear()
    keyboard_y_start = WINDOW_HEIGHT - white_key_height
    for i in range(NUM_WHITE_KEYS):
        white_key_x = i * white_key_width; white_key_rect = pygame.Rect(white_key_x, keyboard_y_start, white_key_width, white_key_height)
        last_drawn_white_key_rects.append(white_key_rect)
        draw_white_key(surface, white_key_rect, SHADOW_OFFSET, white_key_pressed_states[i])
    black_key_pattern = [True, True, False, True, True, True, False]; black_key_idx_counter = 0
    for i in range(NUM_WHITE_KEYS):
        if black_key_pattern[i % 7] and i < NUM_WHITE_KEYS -1:
            if black_key_idx_counter < NUM_BLACK_KEYS:
                black_key_x = (i + 1) * white_key_width - (black_key_width // 2); black_key_rect = pygame.Rect(black_key_x, keyboard_y_start, black_key_width, black_key_height)
                last_drawn_black_key_rects.append(black_key_rect)
                draw_black_key(surface, black_key_rect, SHADOW_OFFSET, black_key_pressed_states[black_key_idx_counter]); black_key_idx_counter += 1
clock = pygame.time.Clock(); running = True
while running:
    dt_ms = clock.get_time()
    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

        elif event.type == DOWNLOAD_COMPLETE_EVENT:
            print(f"Received DOWNLOAD_COMPLETE_EVENT: Status: {event.status}, Msg: {event.message}, Path: {event.filepath if hasattr(event, 'filepath') else 'N/A'}")
            search_status = event.status
            search_feedback_message = event.message
            if event.status == 'DOWNLOAD_SUCCESS':
                if hasattr(event, 'filepath') and event.filepath:
                    print(f"Download successful. File at: {event.filepath}")
                    parse_midi_to_song_data(event.filepath)
                else:
                    search_status = 'ERROR'; search_feedback_message = "Download success, but no filepath."
            elif event.status.startswith('DOWNLOAD_ERROR') or event.status.startswith('SEARCH_ERROR'):
                print(f"Error during download/search: {event.message}")
            elif event.status == 'PARSE_ERROR':
                print(f"Error parsing MIDI: {event.message}")
            elif event.status == 'SUCCESS_PARSE': # New status from parse_midi_to_song_data
                print(f"Successfully parsed and loaded: {os.path.basename(event.filepath if hasattr(event, 'filepath') else 'Unknown file')}")
                # song_data is already updated by parse_midi_to_song_data
                # search_feedback_message is already set
                search_status = 'IDLE' # Or 'READY_TO_PLAY'

        elif event.type == pygame.KEYDOWN:
            if mode_switch_confirm_active:
                if event.key == pygame.K_r: current_mode = target_mode_on_confirm; song_playback_status = 'STOPPED'; current_song_time_seconds = 0.0; song_time_at_last_event = 0.0; real_ticks_at_last_event = 0; reset_song_played_states(song_data); reset_learning_mode_specific_states(); mode_switch_confirm_active = False; target_mode_on_confirm = None
                elif event.key == pygame.K_c: current_mode = target_mode_on_confirm;
                    if song_playback_status == 'USER_PAUSED': song_time_at_last_event = current_song_time_seconds; real_ticks_at_last_event = pygame.time.get_ticks(); song_playback_status = 'PLAYING'
                    if current_mode == APP_MODES['LEARNING']: reset_learning_mode_specific_states()
                    mode_switch_confirm_active = False; target_mode_on_confirm = None
                elif event.key == pygame.K_ESCAPE:
                    if song_playback_status == 'USER_PAUSED': song_time_at_last_event = current_song_time_seconds; real_ticks_at_last_event = pygame.time.get_ticks(); song_playback_status = 'PLAYING'
                    mode_switch_confirm_active = False; target_mode_on_confirm = None
            elif search_input_active:
                if event.key == pygame.K_BACKSPACE: search_input_text = search_input_text[:-1]
                elif event.key == pygame.K_RETURN:
                    print(f"Search triggered by Enter: {search_input_text}")
                    if search_input_text.strip():
                        search_status = 'SEARCHING'
                        search_feedback_message = f"Searching for '{search_input_text}'..."
                        thread = threading.Thread(target=downloader_thread_target, args=(search_input_text,), daemon=True)
                        thread.start()
                    else: search_feedback_message = "Please enter a song title to search."
                    search_input_active = False
                elif event.key == pygame.K_ESCAPE: search_input_active = False
                else: search_input_text += event.unicode
            elif current_mode == APP_MODES['LEARNING'] and learning_mode_state['paused_at_time'] is not None:
                pressed_midi = pc_key_to_midi_map.get(event.key); expected_midi_notes_set = {n['midi_note'] for n in learning_mode_state['notes_at_pause']}
                if event.key == pygame.K_SPACE: song_time_at_last_event = current_song_time_seconds; real_ticks_at_last_event = pygame.time.get_ticks()
                    for note_info_to_skip in learning_mode_state['notes_at_pause']:
                        for song_note in song_data:
                            if song_note['midi_note'] == note_info_to_skip['midi_note'] and song_note['start_time'] == note_info_to_skip['start_time']: song_note['played'] = True; break
                    learning_mode_state['paused_at_time'] = None; learning_mode_state['notes_at_pause'].clear(); learning_mode_state['correctly_pressed_midi_in_pause'].clear()
                elif pressed_midi is not None:
                    if pressed_midi in expected_midi_notes_set and pressed_midi not in learning_mode_state['correctly_pressed_midi_in_pause']:
                        learning_mode_state['correctly_pressed_midi_in_pause'].add(pressed_midi); feedback_flash_info = {'key_midi': pressed_midi, 'color': (0, 255, 0), 'end_time_ms': pygame.time.get_ticks() + 300}
                        if correct_sound: correct_sound.play()
                        key_type_flash, key_idx_flash = get_key_type_and_index_for_midi(pressed_midi, KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, NUM_BLACK_KEYS)
                        if key_type_flash == 'white': white_key_pressed_states[key_idx_flash] = True
                        elif key_type_flash == 'black': black_key_pressed_states[key_idx_flash] = True
                        key_rect = get_rect_for_midi_note(pressed_midi)
                        if key_rect: active_shockwaves.append({'center_x': key_rect.centerx, 'center_y': key_rect.centery, 'start_time_ms': pygame.time.get_ticks(), 'max_radius': white_key_width * 2.0, 'duration_ms': 2000, 'color': ACCENT_COLOR_CYAN })
                        if learning_mode_state['correctly_pressed_midi_in_pause'] == expected_midi_notes_set:
                            song_time_at_last_event = current_song_time_seconds; real_ticks_at_last_event = pygame.time.get_ticks()
                            for note_info_completed in learning_mode_state['notes_at_pause']:
                                for song_note in song_data:
                                    if song_note['midi_note'] == note_info_completed['midi_note'] and song_note['start_time'] == note_info_completed['start_time']: song_note['played'] = True; break
                            for midi_val_release in learning_mode_state['correctly_pressed_midi_in_pause']:
                                k_type_release, k_idx_release = get_key_type_and_index_for_midi(midi_val_release, KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, NUM_BLACK_KEYS)
                                if k_type_release == 'white': white_key_pressed_states[k_idx_release] = False
                                elif k_type_release == 'black': black_key_pressed_states[k_idx_release] = False
                            learning_mode_state['paused_at_time'] = None; learning_mode_state['notes_at_pause'].clear(); learning_mode_state['correctly_pressed_midi_in_pause'].clear()
                    elif pressed_midi not in expected_midi_notes_set: feedback_flash_info = {'key_midi': pressed_midi, 'color': (255, 0, 0), 'end_time_ms': pygame.time.get_ticks() + 300};
                        if incorrect_sound: incorrect_sound.play()
            elif learning_mode_state['paused_at_time'] is None:
                if event.key in key_map:
                    mapped_key = key_map[event.key]; key_type = mapped_key['type']; key_index = mapped_key['index']
                    if key_type == 'white': white_key_pressed_states[key_index] = True
                    elif key_type == 'black': black_key_pressed_states[key_index] = True
                    if mapped_key['sound_obj']: mapped_key['sound_obj'].play()
        elif event.type == pygame.KEYUP: # Moved KEYUP after KEYDOWN
            if not mode_switch_confirm_active and not (current_mode == APP_MODES['LEARNING'] and learning_mode_state['paused_at_time'] is not None):
                if event.key in key_map:
                    mapped_key = key_map[event.key]; key_type = mapped_key['type']; key_index = mapped_key['index']
                    if key_type == 'white': white_key_pressed_states[key_index] = False
                    elif key_type == 'black': black_key_pressed_states[key_index] = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Moved MOUSEBUTTONDOWN after KEYUP
            clicked_action_id = None
            all_clickable_buttons_for_event = [search_button_props_dict] + control_panel_buttons
            for button_info in all_clickable_buttons_for_event:
                if button_info.get('rect') and button_info['rect'].collidepoint(mouse_pos):
                    clicked_action_id = button_info['action_id']; break

            if clicked_action_id:
                if clicked_action_id == 'action_search_midi':
                    if search_input_text.strip():
                        search_status = 'SEARCHING'
                        search_feedback_message = f"Searching for '{search_input_text}'..."
                        thread = threading.Thread(target=downloader_thread_target, args=(search_input_text,), daemon=True)
                        thread.start()
                    else:
                        search_feedback_message = "Please enter a song title to search."
                    search_input_active = False
                elif clicked_action_id == 'action_start':
                    if song_playback_status == 'STOPPED': current_song_time_seconds = 0.0; reset_song_played_states(song_data); reset_learning_mode_specific_states(); song_time_at_last_event = 0.0; real_ticks_at_last_event = pygame.time.get_ticks()
                    elif song_playback_status == 'USER_PAUSED': song_time_at_last_event = current_song_time_seconds; real_ticks_at_last_event = pygame.time.get_ticks()
                    song_playback_status = 'PLAYING'
                    if current_mode == APP_MODES['LEARNING']: learning_mode_state['paused_at_time'] = None
                elif clicked_action_id == 'action_pause':
                    can_user_pause = not (current_mode == APP_MODES['LEARNING'] and learning_mode_state['paused_at_time'] is not None)
                    if song_playback_status == 'PLAYING' and can_user_pause: song_playback_status = 'USER_PAUSED'; time_paused_at_ticks = pygame.time.get_ticks()
                elif clicked_action_id == 'action_stop': song_playback_status = 'STOPPED'; current_song_time_seconds = 0.0; song_time_at_last_event = 0.0; real_ticks_at_last_event = 0; reset_song_played_states(song_data); reset_learning_mode_specific_states()
                elif clicked_action_id == 'action_toggle_mode':
                    if not mode_switch_confirm_active: target_mode_on_confirm = APP_MODES['PRESENTATION'] if current_mode == APP_MODES['LEARNING'] else APP_MODES['LEARNING']; mode_switch_confirm_active = True
                        if song_playback_status == 'PLAYING': song_playback_status = 'USER_PAUSED'; time_paused_at_ticks = pygame.time.get_ticks()

            elif search_input_field_rect.collidepoint(mouse_pos):
                search_input_active = True
            else:
                search_input_active = False
                if tempo_slider_props.get('knob_rect') and tempo_slider_props['knob_rect'].collidepoint(mouse_pos): dragging_tempo_slider = True
                elif tempo_slider_props.get('rect') and tempo_slider_props['rect'].collidepoint(mouse_pos):
                    dragging_tempo_slider = True; click_ratio = max(0.0, min(1.0, (mouse_pos[0] - tempo_slider_props['rect'].left) / tempo_slider_props['rect'].width)); min_val, max_val = tempo_slider_props['value_range']; new_value = min_val + click_ratio * (max_val - min_val)
                    if tempo_multiplier != new_value: song_time_at_last_event = current_song_time_seconds; real_ticks_at_last_event = pygame.time.get_ticks(); tempo_multiplier = new_value
                elif volume_slider_props.get('knob_rect') and volume_slider_props['knob_rect'].collidepoint(mouse_pos): dragging_volume_slider = True
                elif volume_slider_props.get('rect') and volume_slider_props['rect'].collidepoint(mouse_pos):
                    dragging_volume_slider = True; click_ratio = max(0.0, min(1.0, (mouse_pos[0] - volume_slider_props['rect'].left) / volume_slider_props['rect'].width)); min_val, max_val = volume_slider_props['value_range']; global_volume = min_val + click_ratio * (max_val - min_val); set_global_application_volume(global_volume)
                elif progress_bar_props.get('rect') and progress_bar_props['rect'].collidepoint(mouse_pos):
                    if total_song_duration_seconds > 0:
                        click_ratio = max(0.0, min(1.0, (mouse_pos[0] - progress_bar_props['rect'].left) / progress_bar_props['rect'].width)); new_time = click_ratio * total_song_duration_seconds; current_song_time_seconds = new_time
                        song_time_at_last_event = current_song_time_seconds; real_ticks_at_last_event = pygame.time.get_ticks()
                        if song_playback_status == 'USER_PAUSED': time_paused_at_ticks = real_ticks_at_last_event
                        reset_song_played_states(song_data); reset_learning_mode_specific_states()
                        if current_mode == APP_MODES['LEARNING']: learning_mode_state['paused_at_time'] = None
                        print(f"Progress bar clicked, seek to {current_song_time_seconds:.2f}s")
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1: dragging_tempo_slider = False; dragging_volume_slider = False # Moved MOUSEBUTTONUP after MOUSEBUTTONDOWN
        elif event.type == pygame.MOUSEMOTION: # Moved MOUSEMOTION after MOUSEBUTTONUP
            # mouse_pos already updated at the start of the event loop.
            if dragging_tempo_slider and tempo_slider_props.get('rect'):
                slider_rect = tempo_slider_props['rect']; click_ratio = max(0.0, min(1.0, (mouse_pos[0] - slider_rect.left) / slider_rect.width)); min_val, max_val = tempo_slider_props['value_range']; new_value = min_val + click_ratio * (max_val - min_val)
                if tempo_multiplier != new_value: song_time_at_last_event = current_song_time_seconds; real_ticks_at_last_event = pygame.time.get_ticks(); tempo_multiplier = new_value
            elif dragging_volume_slider and volume_slider_props.get('rect'):
                slider_rect = volume_slider_props['rect']; click_ratio = max(0.0, min(1.0, (mouse_pos[0] - slider_rect.left) / slider_rect.width)); min_val, max_val = volume_slider_props['value_range']; global_volume = min_val + click_ratio * (max_val - min_val); set_global_application_volume(global_volume)

    update_stars(stars, dt_ms)

    if song_playback_status == 'PLAYING':
        real_elapsed_ticks_since_event = pygame.time.get_ticks() - real_ticks_at_last_event
        real_elapsed_seconds_since_event = real_elapsed_ticks_since_event / 1000.0
        current_song_time_seconds = song_time_at_last_event + (real_elapsed_seconds_since_event * tempo_multiplier)
        if total_song_duration_seconds > 0 and current_song_time_seconds >= total_song_duration_seconds:
            current_song_time_seconds = total_song_duration_seconds
        if current_mode == APP_MODES['LEARNING']:
            if learning_mode_state['paused_at_time'] is None:
                min_next_note_time = float('inf')
                for note_info_iter in song_data:
                    if not note_info_iter['played'] and note_info_iter['start_time'] < min_next_note_time: min_next_note_time = note_info_iter['start_time']
                if min_next_note_time != float('inf') and min_next_note_time <= current_song_time_seconds:
                    learning_mode_state['paused_at_time'] = min_next_note_time; learning_mode_state['notes_at_pause'].clear()
                    for note_info_iter in song_data:
                        if not note_info_iter['played'] and note_info_iter['start_time'] == min_next_note_time: learning_mode_state['notes_at_pause'].append(dict(note_info_iter))
                    learning_mode_state['correctly_pressed_midi_in_pause'].clear(); current_song_time_seconds = min_next_note_time
                    song_time_at_last_event = current_song_time_seconds; real_ticks_at_last_event = pygame.time.get_ticks()
        elif current_mode == APP_MODES['PRESENTATION']:
            for note_info_pres in song_data:
                key_type_pres, key_idx_pres = get_key_type_and_index_for_midi(note_info_pres['midi_note'], KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, NUM_BLACK_KEYS)
                if key_type_pres is None: continue
                if not note_info_pres['played'] and note_info_pres['start_time'] <= current_song_time_seconds:
                    if key_type_pres == 'white': white_key_pressed_states[key_idx_pres] = True
                    elif key_type_pres == 'black': black_key_pressed_states[key_idx_pres] = True
                    if note_info_pres['midi_note'] in midi_to_sound_map and midi_to_sound_map[note_info_pres['midi_note']]: midi_to_sound_map[note_info_pres['midi_note']].play()
                    note_info_pres['played'] = True
                note_end_time_pres = note_info_pres['start_time'] + note_info_pres['duration']
                if note_info_pres['played'] and note_end_time_pres <= current_song_time_seconds:
                    if key_type_pres == 'white': white_key_pressed_states[key_idx_pres] = False
                    elif key_type_pres == 'black': black_key_pressed_states[key_idx_pres] = False

    screen.fill(BACKGROUND_COLOR)
    draw_stars(screen, stars)
    draw_control_panel(screen, control_panel_buttons, sliders_list, progress_bar_props,
                       current_mode, APP_MODES, mouse_pos,
                       current_song_time_seconds, total_song_duration_seconds, base_bpm,
                       dragging_tempo_slider, dragging_volume_slider,
                       search_input_text, search_input_active, search_feedback_message)
    if current_mode == APP_MODES['PRESENTATION'] or current_mode == APP_MODES['LEARNING']:
        time_for_roll = learning_mode_state['paused_at_time'] if current_mode == APP_MODES['LEARNING'] and learning_mode_state['paused_at_time'] is not None else current_song_time_seconds
        if pixels_per_second > 0:
            for note in song_data:
                note_end_time = note['start_time'] + note['duration']
                if note['start_time'] < time_for_roll + PIANO_ROLL_LOOKAHEAD_SECONDS and note_end_time > time_for_roll:
                    x_center = get_x_for_midi_note(note['midi_note'], KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, white_key_width)
                    if x_center is None: continue
                    semitone = note['midi_note'] % 12; white_note_semitones = [0, 2, 4, 5, 7, 9, 11]; is_white_note = semitone in white_note_semitones
                    rect_width = white_key_width * NOTE_RECT_WIDTH_WHITE_RATIO if is_white_note else black_key_width * NOTE_RECT_WIDTH_BLACK_RATIO
                    rect_left_x = x_center - (rect_width / 2); time_offset_sec_roll = note['start_time'] - time_for_roll; y_offset_px_roll = time_offset_sec_roll * pixels_per_second
                    note_bottom_y_on_roll = PIANO_ROLL_BOTTOM_Y - y_offset_px_roll; note_height_px = note['duration'] * px_per_sec; note_top_y_on_roll = note_bottom_y_on_roll - note_height_px
                    visible_top_y = max(note_top_y_on_roll, PIANO_ROLL_TOP_Y); visible_bottom_y = min(note_bottom_y_on_roll, PIANO_ROLL_BOTTOM_Y); visible_height = visible_bottom_y - visible_top_y
                    if visible_height > 0: note_rect = pygame.Rect(rect_left_x, visible_top_y, rect_width, visible_height); pygame.draw.rect(screen, NOTE_RECT_COLOR, note_rect); pygame.draw.rect(screen, NOTE_RECT_BORDER_COLOR, note_rect, 1)
    draw_piano(screen, white_key_pressed_states, black_key_pressed_states)
    manage_shockwaves(screen, active_shockwaves, pygame.time.get_ticks(), KEYBOARD_RENDER_AREA_RECT)
    if feedback_flash_info['key_midi'] is not None and feedback_flash_info['end_time_ms'] > pygame.time.get_ticks():
        flash_info = feedback_flash_info; key_type_f, key_idx_f = get_key_type_and_index_for_midi(flash_info['key_midi'], KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, NUM_BLACK_KEYS)
        if key_type_f is not None:
            key_center_x_f = get_x_for_midi_note(flash_info['key_midi'], KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, white_key_width)
            if key_center_x_f is not None:
                flash_rect_f = None
                if key_type_f == 'white': flash_rect_f = pygame.Rect(key_center_x_f - white_key_width/2, WINDOW_HEIGHT - keyboard_height, white_key_width, white_key_height)
                elif key_type_f == 'black': flash_rect_f = pygame.Rect(key_center_x_f - black_key_width/2, WINDOW_HEIGHT - keyboard_height, black_key_width, black_key_height)
                if flash_rect_f: flash_surface_f = pygame.Surface(flash_rect_f.size, pygame.SRCALPHA); flash_surface_f.fill((*flash_info['color'], 128)); screen.blit(flash_surface_f, flash_rect_f.topleft)
        else: feedback_flash_info['key_midi'] = None
    else: feedback_flash_info['key_midi'] = None
    if mode_switch_confirm_active:
        overlay_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA); overlay_surface.fill((0, 0, 0, 180)); screen.blit(overlay_surface, (0,0))
        target_mode_name = "Presentation" if target_mode_on_confirm == APP_MODES['PRESENTATION'] else "Learning"
        prompts = [f"Switch to {target_mode_name} Mode?", "Reset song (R) or Continue current position (C)?", "Press Esc to Cancel."]
        text_y_start = WINDOW_HEIGHT // 2 - 50
        for i_prompt, prompt_text in enumerate(prompts):
            surf = control_panel_font.render(prompt_text, True, WHITE); rect = surf.get_rect(center=(WINDOW_WIDTH // 2, text_y_start + i_prompt * 30)); screen.blit(surf, rect)
    pygame.display.flip()
    clock.tick(30)
pygame.quit()
sys.exit()
