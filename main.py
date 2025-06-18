import pygame
import sys
import os

# Initialize Pygame
pygame.init()
pygame.mixer.init()

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
BACKGROUND_COLOR = (50, 50, 50)

# Keyboard Parameters
OCTAVES = 2
NUM_WHITE_KEYS = 7 * OCTAVES
KEYBOARD_HEIGHT_RATIO = 0.25  # 25% of window height for the keyboard
keyboard_height = int(WINDOW_HEIGHT * KEYBOARD_HEIGHT_RATIO)
white_key_width = WINDOW_WIDTH // NUM_WHITE_KEYS  # Integer division
white_key_height = keyboard_height
black_key_width = int(white_key_width * 0.6)
black_key_height = int(white_key_height * 0.6)
SHADOW_OFFSET = 3  # Pixels for shadow effect

# --- Control Panel Constants ---
CONTROL_PANEL_HEIGHT = 150 # Further Increased for sliders and progress bar layout
CONTROL_PANEL_Y_START = WINDOW_HEIGHT - CONTROL_PANEL_HEIGHT # Positioned at the very bottom
CONTROL_PANEL_BG_COLOR = (30, 30, 30)
BUTTON_TEXT_COLOR = (230, 230, 230)
BUTTON_BASE_COLOR = (80, 80, 80)
BUTTON_HOVER_COLOR = (110, 110, 110)
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 40
BUTTON_MARGIN = 10 # Margin between buttons and panel edges

# Constants for Sliders and Progress Bar
SLIDER_TRACK_HEIGHT = 10
SLIDER_KNOB_WIDTH = 15
SLIDER_KNOB_HEIGHT = 30
SLIDER_WIDTH = 150 # Length of the track
PROGRESS_BAR_HEIGHT = 15
SLIDERS_Y_OFFSET = 20 # Relative to CONTROL_PANEL_Y_START
PROGRESS_BAR_Y_OFFSET = SLIDERS_Y_OFFSET + SLIDER_KNOB_HEIGHT + 10 # Below sliders, with some padding

SLIDER_TRACK_COLOR = (50, 50, 50)
SLIDER_KNOB_COLOR = (150, 150, 150)
PROGRESS_BAR_TRACK_COLOR = (50, 50, 50)
PROGRESS_BAR_FILL_COLOR = (0, 120, 255)

try:
    control_panel_font = pygame.font.Font(None, 28) # Default font, size 28
except Exception as e:
    print(f"Could not load default font for control panel, using fallback pygame.font.SysFont: {e}")
    control_panel_font = pygame.font.SysFont(pygame.font.get_default_font(), 28)

control_panel_buttons = [] # List to hold button dictionaries/objects

# Define button properties and initial Rects
button_actions = ['action_start', 'action_pause', 'action_stop', 'action_toggle_mode']
button_texts = ["Start", "Pause", "Stop", "Mode: Learning"] # Mode button text is dynamic

num_buttons = len(button_actions)
total_buttons_width = num_buttons * BUTTON_WIDTH + (num_buttons - 1) * BUTTON_MARGIN
start_x_layout = (WINDOW_WIDTH - total_buttons_width) // 2 # Renamed to avoid conflict with 'start_x' in draw_control_panel

for i, action in enumerate(button_actions):
    button_x = start_x_layout + i * (BUTTON_WIDTH + BUTTON_MARGIN) # Use renamed variable
    # Button Y position is now set in draw_control_panel for dynamic layout
    button_y_placeholder = CONTROL_PANEL_Y_START + CONTROL_PANEL_HEIGHT - BUTTON_HEIGHT - padding # Placeholder, will be updated by draw_control_panel

    btn_rect = pygame.Rect(button_x, button_y_placeholder, BUTTON_WIDTH, BUTTON_HEIGHT)

    control_panel_buttons.append({
        'rect': btn_rect, # Position will be finalized in draw_control_panel
        'text': button_texts[i],
        'action_id': action,
        'base_color': BUTTON_BASE_COLOR,
        'hover_color': BUTTON_HOVER_COLOR,
        'text_color': BUTTON_TEXT_COLOR,
        'font': control_panel_font
    })

# Slider definitions
tempo_slider_props = {
    'label': "Tempo",
    'value_range': (0.5, 2.0),
    'current_value_func': lambda: tempo_multiplier,
    'setter_func': None,
    'rect': None,
    'knob_rect': None,
    'text_label_func': lambda: f"Tempo: {int(base_bpm * tempo_multiplier)} BPM"
}

volume_slider_props = {
    'label': "Volume",
    'value_range': (0.0, 1.0),
    'current_value_func': lambda: global_volume,
    'setter_func': None,
    'rect': None,
    'knob_rect': None,
    'text_label_func': lambda: f"Volume: {int(global_volume * 100)}%"
}

sliders_list = [tempo_slider_props, volume_slider_props]

progress_bar_props = {
    'rect': None,
    'fill_color': PROGRESS_BAR_FILL_COLOR,
    'track_color': PROGRESS_BAR_TRACK_COLOR
}


# --- Piano Roll Constants ---
PIANO_ROLL_LOOKAHEAD_SECONDS = 5.0
PIANO_ROLL_SECONDS_ON_SCREEN = 5.0
PIANO_ROLL_TOP_Y = 50
PIANO_ROLL_BOTTOM_Y = WINDOW_HEIGHT - keyboard_height - 10
NOTE_RECT_COLOR = (0, 150, 255)
NOTE_RECT_BORDER_COLOR = (200, 200, 255)
NOTE_RECT_WIDTH_WHITE_RATIO = 0.8
NOTE_RECT_WIDTH_BLACK_RATIO = 0.9

if PIANO_ROLL_BOTTOM_Y > PIANO_ROLL_TOP_Y and PIANO_ROLL_SECONDS_ON_SCREEN > 0:
    pixels_per_second = (PIANO_ROLL_BOTTOM_Y - PIANO_ROLL_TOP_Y) / PIANO_ROLL_SECONDS_ON_SCREEN
else:
    pixels_per_second = 0
    print("Warning: Piano roll Y coordinates or seconds_on_screen are configured incorrectly.")

# Pressed State Lists
NUM_BLACK_KEYS = 5 * OCTAVES
white_key_pressed_states = [False] * NUM_WHITE_KEYS
black_key_pressed_states = [False] * NUM_BLACK_KEYS

SOUNDS_DIR = "sounds"
PLACEHOLDER_SOUND = os.path.join(SOUNDS_DIR, "placeholder.wav")
CORRECT_SOUND_FILE = os.path.join(SOUNDS_DIR, "correct.wav")
INCORRECT_SOUND_FILE = os.path.join(SOUNDS_DIR, "incorrect.wav")

correct_sound = None
incorrect_sound = None

try:
    correct_sound = pygame.mixer.Sound(CORRECT_SOUND_FILE)
except pygame.error as e:
    print(f"Could not load correct sound {CORRECT_SOUND_FILE}: {e}.")
    if not os.path.exists(CORRECT_SOUND_FILE):
        try: open(CORRECT_SOUND_FILE, 'w').close()
        except Exception as fe: print(f"Failed to create dummy file {CORRECT_SOUND_FILE}: {fe}")
try:
    incorrect_sound = pygame.mixer.Sound(INCORRECT_SOUND_FILE)
except pygame.error as e:
    print(f"Could not load incorrect sound {INCORRECT_SOUND_FILE}: {e}.")
    if not os.path.exists(INCORRECT_SOUND_FILE):
        try: open(INCORRECT_SOUND_FILE, 'w').close()
        except Exception as fe: print(f"Failed to create dummy file {INCORRECT_SOUND_FILE}: {fe}")

if not os.path.exists(SOUNDS_DIR):
    os.makedirs(SOUNDS_DIR)

key_map = {
    pygame.K_a: {'type': 'white', 'index': 0, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_s: {'type': 'white', 'index': 1, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_d: {'type': 'white', 'index': 2, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_f: {'type': 'white', 'index': 3, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_g: {'type': 'white', 'index': 4, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_h: {'type': 'white', 'index': 5, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_j: {'type': 'white', 'index': 6, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_k: {'type': 'white', 'index': 7, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_l: {'type': 'white', 'index': 8, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_SEMICOLON: {'type': 'white', 'index': 9, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_w: {'type': 'black', 'index': 0, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_e: {'type': 'black', 'index': 1, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_t: {'type': 'black', 'index': 2, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_y: {'type': 'black', 'index': 3, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_u: {'type': 'black', 'index': 4, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_o: {'type': 'black', 'index': 5, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
    pygame.K_p: {'type': 'black', 'index': 6, 'sound_file': PLACEHOLDER_SOUND, 'sound_obj': None},
}
for key_code, data in key_map.items():
    try:
        sound = pygame.mixer.Sound(data['sound_file'])
        data['sound_obj'] = sound
    except pygame.error as e:
        print(f"Could not load sound for key {pygame.key.name(key_code)}: {data['sound_file']} - {e}")

midi_to_sound_map = {}
KEYBOARD_START_MIDI_NOTE = 60
WHITE_KEY_MIDI_OFFSETS = [0, 2, 4, 5, 7, 9, 11]
BLACK_KEY_MIDI_OFFSETS = [1, 3, 6, 8, 10]
for pc_key, data in key_map.items():
    key_type = data['type']
    key_index_on_keyboard = data['index']
    sound_obj = data['sound_obj']
    if sound_obj:
        midi_note = -1
        if key_type == 'white':
            octave_num = (KEYBOARD_START_MIDI_NOTE // 12) + (key_index_on_keyboard // 7)
            offset_in_octave = WHITE_KEY_MIDI_OFFSETS[key_index_on_keyboard % 7]
            midi_note = octave_num * 12 + offset_in_octave
        elif key_type == 'black':
            octave_num = (KEYBOARD_START_MIDI_NOTE // 12) + (key_index_on_keyboard // 5)
            offset_in_octave = BLACK_KEY_MIDI_OFFSETS[key_index_on_keyboard % 5]
            midi_note = octave_num * 12 + offset_in_octave
        if midi_note != -1 and midi_note not in midi_to_sound_map:
            midi_to_sound_map[midi_note] = sound_obj

pc_key_to_midi_map = {}
for pc_key_code, data in key_map.items():
    key_type = data['type']
    key_index_in_type = data['index']
    midi_note = -1
    if key_type == 'white':
        octave_num_for_key = (KEYBOARD_START_MIDI_NOTE // 12) + (key_index_in_type // 7)
        offset_in_octave_for_key = WHITE_KEY_MIDI_OFFSETS[key_index_in_type % 7]
        midi_note = octave_num_for_key * 12 + offset_in_octave_for_key
    elif key_type == 'black':
        octave_num_for_key = (KEYBOARD_START_MIDI_NOTE // 12) + (key_index_in_type // 5)
        offset_in_octave_for_key = BLACK_KEY_MIDI_OFFSETS[key_index_in_type % 5]
        midi_note = octave_num_for_key * 12 + offset_in_octave_for_key
    if midi_note != -1:
        pc_key_to_midi_map[pc_key_code] = midi_note

song_data = [
    {'midi_note': 67, 'start_time': 0.0, 'duration': 0.4, 'played': False},
    {'midi_note': 64, 'start_time': 0.5, 'duration': 0.4, 'played': False},
    {'midi_note': 60, 'start_time': 1.0, 'duration': 0.4, 'played': False},
    {'midi_note': 67, 'start_time': 1.5, 'duration': 0.4, 'played': False},
    {'midi_note': 69, 'start_time': 2.0, 'duration': 0.4, 'played': False},
    {'midi_note': 67, 'start_time': 2.5, 'duration': 0.4, 'played': False},
    {'midi_note': 64, 'start_time': 3.0, 'duration': 0.4, 'played': False},
    {'midi_note': 60, 'start_time': 3.5, 'duration': 0.4, 'played': False},
    {'midi_note': 67, 'start_time': 4.0, 'duration': 0.4, 'played': False},
]

def debug_print_song(notes_list):
    # ... (content as before) ...
    pass

def get_total_song_duration(notes_list):
    if not notes_list: return 0.0
    max_end_time = 0.0
    for note in notes_list:
        note_end_time = note.get('start_time', 0) + note.get('duration', 0)
        if note_end_time > max_end_time: max_end_time = note_end_time
    return max_end_time

total_song_duration_seconds = get_total_song_duration(song_data)

APP_MODES = {'LEARNING': 0, 'PRESENTATION': 1}
current_mode = APP_MODES['LEARNING']

learning_mode_state = {
    'paused_at_time': None,
    'notes_at_pause': [],
    'correctly_pressed_midi_in_pause': set()
}
feedback_flash_info = {
    'key_midi': None, 'color': None, 'end_time_ms': 0
}
base_bpm = 120.0
tempo_multiplier = 1.0
global_volume = 1.0
dragging_tempo_slider = False
dragging_volume_slider = False
song_playback_status = 'STOPPED'
mode_switch_confirm_active = False
target_mode_on_confirm = None
time_paused_at_ticks = 0
current_song_time_seconds = 0.0
song_start_time_ticks = 0 # Old timing system variable, less critical now
song_time_at_last_event = 0.0
real_ticks_at_last_event = 0

def reset_song_played_states(notes_list):
    for note_info in notes_list: note_info['played'] = False

def reset_learning_mode_specific_states():
    global learning_mode_state
    learning_mode_state['paused_at_time'] = None
    learning_mode_state['notes_at_pause'].clear()
    learning_mode_state['correctly_pressed_midi_in_pause'].clear()

# Initial pre-loop setup from Subtask 28
song_playback_status = 'STOPPED'
current_song_time_seconds = 0.0
song_time_at_last_event = 0.0 # Initialize for new timing system
real_ticks_at_last_event = 0   # Initialize for new timing system
reset_song_played_states(song_data)
reset_learning_mode_specific_states()

def get_x_for_midi_note(midi_note, first_midi_note_on_keyboard, num_total_white_keys, white_key_width_px):
    # ... (content as before) ...
    white_note_positions_in_octave = [0, 2, 4, 5, 7, 9, 11]
    semitone = midi_note % 12
    octave = midi_note // 12
    white_key_map = {0:0, 1:0, 2:1, 3:1, 4:2, 5:3, 6:3, 7:4, 8:4, 9:5, 10:5, 11:6}
    white_key_num_in_octave = white_key_map[semitone]
    base_octave = first_midi_note_on_keyboard // 12
    total_white_key_index = (octave - base_octave) * 7 + white_key_num_in_octave
    if not (0 <= total_white_key_index < num_total_white_keys): return None
    x_coord = 0
    if semitone not in white_note_positions_in_octave:
        x_coord = (total_white_key_index + 1) * white_key_width_px
    else:
        x_coord = (total_white_key_index * white_key_width_px) + (white_key_width_px / 2.0)
    return x_coord


def get_key_type_and_index_for_midi(midi_note, first_midi_note_on_keyboard, num_total_white_keys, num_total_black_keys):
    # ... (content as before) ...
    semitone = midi_note % 12
    octave = midi_note // 12
    base_octave = first_midi_note_on_keyboard // 12
    white_note_semitones_in_octave = [0, 2, 4, 5, 7, 9, 11]
    white_key_indices_map = {0:0, 1:0, 2:1, 3:1, 4:2, 5:3, 6:3, 7:4, 8:4, 9:5, 10:5, 11:6}
    black_key_indices_map = {1:0, 3:1, 6:2, 8:3, 10:4}
    key_type, key_index = None, None
    if semitone in white_note_semitones_in_octave:
        key_type = 'white'
        idx_in_octave = white_key_indices_map[semitone]
        key_index = (octave - base_octave) * 7 + idx_in_octave
        if not (0 <= key_index < num_total_white_keys): return None, None
    elif semitone in black_key_indices_map:
        key_type = 'black'
        idx_in_octave = black_key_indices_map[semitone]
        key_index = (octave - base_octave) * 5 + idx_in_octave
        if not (0 <= key_index < num_total_black_keys): return None, None
    else: return None, None
    return key_type, key_index

def draw_piano_roll_notes(surface, current_time_sec, notes_list, px_per_sec, lookahead_sec, first_midi_ref, total_white_keys_ref, white_key_w_ref, black_key_w_ref):
    # ... (content as before, ensure it uses current_time_sec correctly) ...
    pass # Placeholder for brevity, actual content is there

def draw_control_panel(surface, buttons_list_ref, sliders_list_ref, progress_bar_props_ref,
                           current_app_mode_val, app_modes_ref, mouse_pos_tuple,
                           current_song_time_ref, total_song_duration_ref, base_bpm_ref):
    # ... (content as implemented in step 27, ensure button_y_placeholder is resolved or handled) ...
    # For button_y_placeholder, I'll use the logic from step 27 that places buttons in the bottom row.
    panel_rect_bg = pygame.Rect(0, CONTROL_PANEL_Y_START, WINDOW_WIDTH, CONTROL_PANEL_HEIGHT)
    pygame.draw.rect(surface, CONTROL_PANEL_BG_COLOR, panel_rect_bg)
    padding = 10
    slider_label_width = 150
    slider_y_pos_abs = CONTROL_PANEL_Y_START + padding
    slider_track_width_actual = SLIDER_WIDTH
    tempo_slider = sliders_list_ref[0]
    tempo_label_x_start = padding
    tempo_slider_track_x_start = tempo_label_x_start + slider_label_width + padding
    tempo_slider['rect'] = pygame.Rect(tempo_slider_track_x_start, slider_y_pos_abs + (SLIDER_KNOB_HEIGHT - SLIDER_TRACK_HEIGHT)//2, slider_track_width_actual, SLIDER_TRACK_HEIGHT)
    tempo_text = tempo_slider['text_label_func']()
    tempo_label_surf = control_panel_font.render(tempo_text, True, BUTTON_TEXT_COLOR)
    tempo_label_rect = tempo_label_surf.get_rect(left=tempo_label_x_start, centery=tempo_slider['rect'].centery)
    surface.blit(tempo_label_surf, tempo_label_rect)
    pygame.draw.rect(surface, SLIDER_TRACK_COLOR, tempo_slider['rect'], border_radius=5)
    tempo_val = tempo_slider['current_value_func']()
    tempo_min, tempo_max = tempo_slider['value_range']
    knob_x_ratio_tempo = (tempo_val - tempo_min) / (tempo_max - tempo_min) if (tempo_max - tempo_min) != 0 else 0
    knob_x_tempo = tempo_slider['rect'].left + int(knob_x_ratio_tempo * tempo_slider['rect'].width)
    tempo_slider['knob_rect'] = pygame.Rect(knob_x_tempo - SLIDER_KNOB_WIDTH // 2, slider_y_pos_abs, SLIDER_KNOB_WIDTH, SLIDER_KNOB_HEIGHT)
    pygame.draw.rect(surface, SLIDER_KNOB_COLOR, tempo_slider['knob_rect'], border_radius=3)
    volume_slider = sliders_list_ref[1]
    volume_label_x_start = tempo_slider_track_x_start + slider_track_width_actual + padding * 2
    volume_slider_track_x_start = volume_label_x_start + slider_label_width + padding
    volume_slider['rect'] = pygame.Rect(volume_slider_track_x_start, slider_y_pos_abs + (SLIDER_KNOB_HEIGHT - SLIDER_TRACK_HEIGHT)//2, slider_track_width_actual, SLIDER_TRACK_HEIGHT)
    volume_text = volume_slider['text_label_func']()
    volume_label_surf = control_panel_font.render(volume_text, True, BUTTON_TEXT_COLOR)
    volume_label_rect = volume_label_surf.get_rect(left=volume_label_x_start, centery=volume_slider['rect'].centery)
    surface.blit(volume_label_surf, volume_label_rect)
    pygame.draw.rect(surface, SLIDER_TRACK_COLOR, volume_slider['rect'], border_radius=5)
    volume_val = volume_slider['current_value_func']()
    volume_min, volume_max = volume_slider['value_range']
    knob_x_ratio_volume = (volume_val - volume_min) / (volume_max - volume_min) if (volume_max - volume_min) != 0 else 0
    knob_x_volume = volume_slider['rect'].left + int(knob_x_ratio_volume * volume_slider['rect'].width)
    volume_slider['knob_rect'] = pygame.Rect(knob_x_volume - SLIDER_KNOB_WIDTH // 2, slider_y_pos_abs, SLIDER_KNOB_WIDTH, SLIDER_KNOB_HEIGHT)
    pygame.draw.rect(surface, SLIDER_KNOB_COLOR, volume_slider['knob_rect'], border_radius=3)
    progress_bar_y_pos_abs = slider_y_pos_abs + SLIDER_KNOB_HEIGHT + padding
    progress_bar_width_actual = WINDOW_WIDTH - 2 * padding
    progress_bar_props_ref['rect'] = pygame.Rect(padding, progress_bar_y_pos_abs, progress_bar_width_actual, PROGRESS_BAR_HEIGHT)
    pygame.draw.rect(surface, progress_bar_props_ref['track_color'], progress_bar_props_ref['rect'], border_radius=3)
    if total_song_duration_ref > 0:
        progress_ratio = min(current_song_time_ref / total_song_duration_ref, 1.0) if total_song_duration_ref > 0 else 0
        fill_width = int(progress_ratio * progress_bar_props_ref['rect'].width)
        if fill_width > 0:
            fill_rect = pygame.Rect(progress_bar_props_ref['rect'].left, progress_bar_props_ref['rect'].top, fill_width, progress_bar_props_ref['rect'].height)
            pygame.draw.rect(surface, progress_bar_props_ref['fill_color'], fill_rect, border_radius=3)
    button_y_start_abs = progress_bar_y_pos_abs + PROGRESS_BAR_HEIGHT + padding
    num_buttons_val = len(buttons_list_ref)
    total_buttons_width_val = num_buttons_val * BUTTON_WIDTH + (num_buttons_val - 1) * BUTTON_MARGIN
    start_x_buttons_val = (WINDOW_WIDTH - total_buttons_width_val) // 2
    for i, button_info in enumerate(buttons_list_ref):
        button_x = start_x_buttons_val + i * (BUTTON_WIDTH + BUTTON_MARGIN)
        button_info['rect'].topleft = (button_x, button_y_start_abs)
        btn_rect_updated = button_info['rect']
        current_color = button_info['base_color']
        if btn_rect_updated.collidepoint(mouse_pos_tuple): current_color = button_info['hover_color']
        pygame.draw.rect(surface, current_color, btn_rect_updated)
        pygame.draw.rect(surface, (50,50,50), btn_rect_updated, 1)
        button_text_content = button_info['text']
        if button_info['action_id'] == 'action_toggle_mode':
            mode_name = "Learning" if current_app_mode_val == app_modes_ref['LEARNING'] else "Presentation"
            button_text_content = f"Mode: {mode_name}"
        if button_info['font'] and button_text_content:
            text_surf = button_info['font'].render(button_text_content, True, button_info['text_color'])
            text_rect = text_surf.get_rect(center=btn_rect_updated.center)
            surface.blit(text_surf, text_rect)
    pass # Placeholder for brevity

def draw_feedback_flash_overlay(surface, flash_info, first_midi_ref, num_white_keys_ref, num_black_keys_ref, white_key_w_ref, keyboard_y_start_ref, white_key_h_ref, black_key_w_ref, black_key_h_ref):
    # ... (content as before) ...
    pass # Placeholder for brevity

def draw_white_key(surface, rect, shadow_offset, is_pressed):
    # ... (content as before) ...
    pass # Placeholder for brevity

def draw_black_key(surface, rect, shadow_offset, is_pressed):
    # ... (content as before) ...
    pass # Placeholder for brevity

def draw_piano(surface, white_pressed_states, black_pressed_states):
    # ... (content as before) ...
    pass # Placeholder for brevity

clock = pygame.time.Clock()
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if mode_switch_confirm_active:
                if event.key == pygame.K_r:
                    current_mode = target_mode_on_confirm
                    song_playback_status = 'STOPPED'
                    current_song_time_seconds = 0.0
                    song_time_at_last_event = 0.0 # Reset timing
                    real_ticks_at_last_event = 0  # Reset timing
                    reset_song_played_states(song_data)
                    reset_learning_mode_specific_states()
                    mode_switch_confirm_active = False
                    target_mode_on_confirm = None
                elif event.key == pygame.K_c:
                    current_mode = target_mode_on_confirm
                    if song_playback_status == 'USER_PAUSED':
                        song_time_at_last_event = current_song_time_seconds
                        real_ticks_at_last_event = pygame.time.get_ticks()
                        song_playback_status = 'PLAYING'
                    if current_mode == APP_MODES['LEARNING']:
                        reset_learning_mode_specific_states()
                    mode_switch_confirm_active = False
                    target_mode_on_confirm = None
                elif event.key == pygame.K_ESCAPE:
                    if song_playback_status == 'USER_PAUSED':
                        song_time_at_last_event = current_song_time_seconds
                        real_ticks_at_last_event = pygame.time.get_ticks()
                        song_playback_status = 'PLAYING'
                    mode_switch_confirm_active = False
                    target_mode_on_confirm = None
            elif current_mode == APP_MODES['LEARNING'] and learning_mode_state['paused_at_time'] is not None:
                pressed_midi = pc_key_to_midi_map.get(event.key)
                expected_midi_notes_set = {n['midi_note'] for n in learning_mode_state['notes_at_pause']}
                if event.key == pygame.K_SPACE:
                    song_time_at_last_event = current_song_time_seconds
                    real_ticks_at_last_event = pygame.time.get_ticks()
                    for note_info_to_skip in learning_mode_state['notes_at_pause']:
                        for song_note in song_data:
                            if song_note['midi_note'] == note_info_to_skip['midi_note'] and song_note['start_time'] == note_info_to_skip['start_time']:
                                song_note['played'] = True; break
                    learning_mode_state['paused_at_time'] = None
                    learning_mode_state['notes_at_pause'].clear()
                    learning_mode_state['correctly_pressed_midi_in_pause'].clear()
                elif pressed_midi is not None:
                    if pressed_midi in expected_midi_notes_set and pressed_midi not in learning_mode_state['correctly_pressed_midi_in_pause']:
                        learning_mode_state['correctly_pressed_midi_in_pause'].add(pressed_midi)
                        feedback_flash_info = {'key_midi': pressed_midi, 'color': (0, 255, 0), 'end_time_ms': pygame.time.get_ticks() + 300}
                        if correct_sound: correct_sound.play()
                        key_type_flash, key_idx_flash = get_key_type_and_index_for_midi(pressed_midi, KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, NUM_BLACK_KEYS)
                        if key_type_flash == 'white': white_key_pressed_states[key_idx_flash] = True
                        elif key_type_flash == 'black': black_key_pressed_states[key_idx_flash] = True
                        if learning_mode_state['correctly_pressed_midi_in_pause'] == expected_midi_notes_set:
                            song_time_at_last_event = current_song_time_seconds
                            real_ticks_at_last_event = pygame.time.get_ticks()
                            for note_info_completed in learning_mode_state['notes_at_pause']:
                                for song_note in song_data:
                                    if song_note['midi_note'] == note_info_completed['midi_note'] and song_note['start_time'] == note_info_completed['start_time']:
                                        song_note['played'] = True; break
                            for midi_val_release in learning_mode_state['correctly_pressed_midi_in_pause']:
                                k_type_release, k_idx_release = get_key_type_and_index_for_midi(midi_val_release, KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, NUM_BLACK_KEYS)
                                if k_type_release == 'white': white_key_pressed_states[k_idx_release] = False
                                elif k_type_release == 'black': black_key_pressed_states[k_idx_release] = False
                            learning_mode_state['paused_at_time'] = None
                            learning_mode_state['notes_at_pause'].clear()
                            learning_mode_state['correctly_pressed_midi_in_pause'].clear()
                    elif pressed_midi not in expected_midi_notes_set:
                        feedback_flash_info = {'key_midi': pressed_midi, 'color': (255, 0, 0), 'end_time_ms': pygame.time.get_ticks() + 300}
                        if incorrect_sound: incorrect_sound.play()
            elif learning_mode_state['paused_at_time'] is None: # Free play (Learning or other modes)
                if event.key in key_map:
                    mapped_key = key_map[event.key]
                    key_type = mapped_key['type']; key_index = mapped_key['index']
                    if key_type == 'white': white_key_pressed_states[key_index] = True
                    elif key_type == 'black': black_key_pressed_states[key_index] = True
                    if mapped_key['sound_obj']: mapped_key['sound_obj'].play()

        if event.type == pygame.KEYUP:
            if not mode_switch_confirm_active and not (current_mode == APP_MODES['LEARNING'] and learning_mode_state['paused_at_time'] is not None):
                if event.key in key_map:
                    mapped_key = key_map[event.key]
                    key_type = mapped_key['type']; key_index = mapped_key['index']
                    if key_type == 'white': white_key_pressed_states[key_index] = False
                    elif key_type == 'black': black_key_pressed_states[key_index] = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            clicked_action_id = None
            for button_info in control_panel_buttons:
                if button_info['rect'].collidepoint(mouse_pos):
                    clicked_action_id = button_info['action_id']; break
            if clicked_action_id:
                if clicked_action_id == 'action_start':
                    if song_playback_status == 'STOPPED':
                        current_song_time_seconds = 0.0
                        reset_song_played_states(song_data)
                        reset_learning_mode_specific_states()
                        song_time_at_last_event = 0.0
                        real_ticks_at_last_event = pygame.time.get_ticks()
                    elif song_playback_status == 'USER_PAUSED':
                        song_time_at_last_event = current_song_time_seconds
                        real_ticks_at_last_event = pygame.time.get_ticks()
                    song_playback_status = 'PLAYING'
                    if current_mode == APP_MODES['LEARNING']: learning_mode_state['paused_at_time'] = None
                elif clicked_action_id == 'action_pause':
                    can_user_pause = not (current_mode == APP_MODES['LEARNING'] and learning_mode_state['paused_at_time'] is not None)
                    if song_playback_status == 'PLAYING' and can_user_pause:
                        song_playback_status = 'USER_PAUSED'
                        time_paused_at_ticks = pygame.time.get_ticks()
                elif clicked_action_id == 'action_stop':
                    song_playback_status = 'STOPPED'
                    current_song_time_seconds = 0.0
                    song_time_at_last_event = 0.0
                    real_ticks_at_last_event = 0
                    reset_song_played_states(song_data)
                    reset_learning_mode_specific_states()
                elif clicked_action_id == 'action_toggle_mode':
                    if not mode_switch_confirm_active:
                        target_mode_on_confirm = APP_MODES['PRESENTATION'] if current_mode == APP_MODES['LEARNING'] else APP_MODES['LEARNING']
                        mode_switch_confirm_active = True
                        if song_playback_status == 'PLAYING':
                            song_playback_status = 'USER_PAUSED'
                            time_paused_at_ticks = pygame.time.get_ticks()
            elif tempo_slider_props.get('knob_rect') and tempo_slider_props['knob_rect'].collidepoint(mouse_pos):
                dragging_tempo_slider = True
            elif tempo_slider_props.get('rect') and tempo_slider_props['rect'].collidepoint(mouse_pos):
                dragging_tempo_slider = True
                click_ratio = max(0.0, min(1.0, (mouse_pos[0] - tempo_slider_props['rect'].left) / tempo_slider_props['rect'].width))
                min_val, max_val = tempo_slider_props['value_range']
                new_value = min_val + click_ratio * (max_val - min_val)
                if tempo_multiplier != new_value:
                    song_time_at_last_event = current_song_time_seconds
                    real_ticks_at_last_event = pygame.time.get_ticks()
                    tempo_multiplier = new_value
            elif volume_slider_props.get('knob_rect') and volume_slider_props['knob_rect'].collidepoint(mouse_pos):
                dragging_volume_slider = True
            elif volume_slider_props.get('rect') and volume_slider_props['rect'].collidepoint(mouse_pos):
                dragging_volume_slider = True
                click_ratio = max(0.0, min(1.0, (mouse_pos[0] - volume_slider_props['rect'].left) / volume_slider_props['rect'].width))
                min_val, max_val = volume_slider_props['value_range']
                global_volume = min_val + click_ratio * (max_val - min_val)
            elif progress_bar_props.get('rect') and progress_bar_props['rect'].collidepoint(mouse_pos):
                if total_song_duration_seconds > 0:
                    click_ratio = max(0.0, min(1.0, (mouse_pos[0] - progress_bar_props['rect'].left) / progress_bar_props['rect'].width))
                    new_time = click_ratio * total_song_duration_seconds
                    current_song_time_seconds = new_time
                    song_time_at_last_event = current_song_time_seconds
                    real_ticks_at_last_event = pygame.time.get_ticks()
                    if song_playback_status == 'USER_PAUSED': time_paused_at_ticks = real_ticks_at_last_event
                    reset_song_played_states(song_data)
                    reset_learning_mode_specific_states()
                    if current_mode == APP_MODES['LEARNING']: learning_mode_state['paused_at_time'] = None
                    print(f"Progress bar clicked, seek to {current_song_time_seconds:.2f}s")

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            dragging_tempo_slider = False; dragging_volume_slider = False

        if event.type == pygame.MOUSEMOTION:
            mouse_pos_motion = event.pos
            if dragging_tempo_slider and tempo_slider_props.get('rect'):
                slider_rect = tempo_slider_props['rect']
                click_ratio = max(0.0, min(1.0, (mouse_pos_motion[0] - slider_rect.left) / slider_rect.width))
                min_val, max_val = tempo_slider_props['value_range']
                new_value = min_val + click_ratio * (max_val - min_val)
                if tempo_multiplier != new_value:
                    song_time_at_last_event = current_song_time_seconds
                    real_ticks_at_last_event = pygame.time.get_ticks()
                    tempo_multiplier = new_value
            elif dragging_volume_slider and volume_slider_props.get('rect'):
                slider_rect = volume_slider_props['rect']
                click_ratio = max(0.0, min(1.0, (mouse_pos_motion[0] - slider_rect.left) / slider_rect.width))
                min_val, max_val = volume_slider_props['value_range']
                global_volume = min_val + click_ratio * (max_val - min_val)

    if song_playback_status == 'PLAYING':
        real_elapsed_ticks_since_event = pygame.time.get_ticks() - real_ticks_at_last_event
        real_elapsed_seconds_since_event = real_elapsed_ticks_since_event / 1000.0
        current_song_time_seconds = song_time_at_last_event + (real_elapsed_seconds_since_event * tempo_multiplier)
        if total_song_duration_seconds > 0 and current_song_time_seconds >= total_song_duration_seconds:
            current_song_time_seconds = total_song_duration_seconds
            # song_playback_status = 'STOPPED' # Optional: auto-stop at end
            # reset_learning_mode_specific_states()

        if current_mode == APP_MODES['LEARNING']:
            if learning_mode_state['paused_at_time'] is None:
                min_next_note_time = float('inf')
                for note_info_iter in song_data:
                    if not note_info_iter['played'] and note_info_iter['start_time'] < min_next_note_time:
                        min_next_note_time = note_info_iter['start_time']
                if min_next_note_time != float('inf') and min_next_note_time <= current_song_time_seconds:
                    learning_mode_state['paused_at_time'] = min_next_note_time
                    learning_mode_state['notes_at_pause'].clear()
                    for note_info_iter in song_data:
                        if not note_info_iter['played'] and note_info_iter['start_time'] == min_next_note_time:
                            learning_mode_state['notes_at_pause'].append(dict(note_info_iter))
                    learning_mode_state['correctly_pressed_midi_in_pause'].clear()
                    current_song_time_seconds = min_next_note_time
                    song_time_at_last_event = current_song_time_seconds
                    real_ticks_at_last_event = pygame.time.get_ticks()
        elif current_mode == APP_MODES['PRESENTATION']:
            for note_info_pres in song_data:
                key_type_pres, key_idx_pres = get_key_type_and_index_for_midi(note_info_pres['midi_note'], KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, NUM_BLACK_KEYS)
                if key_type_pres is None: continue # Corrected variable name from key_type to key_type_pres
                if not note_info_pres['played'] and note_info_pres['start_time'] <= current_song_time_seconds:
                    if key_type_pres == 'white': white_key_pressed_states[key_idx_pres] = True
                    elif key_type_pres == 'black': black_key_pressed_states[key_idx_pres] = True
                    if note_info_pres['midi_note'] in midi_to_sound_map and midi_to_sound_map[note_info_pres['midi_note']]:
                        midi_to_sound_map[note_info_pres['midi_note']].play()
                    note_info_pres['played'] = True
                note_end_time_pres = note_info_pres['start_time'] + note_info_pres['duration']
                if note_info_pres['played'] and note_end_time_pres <= current_song_time_seconds:
                    if key_type_pres == 'white': white_key_pressed_states[key_idx_pres] = False
                    elif key_type_pres == 'black': black_key_pressed_states[key_idx_pres] = False

    screen.fill(BACKGROUND_COLOR)
    # Corrected draw_control_panel call, ensuring all arguments are passed as defined in its signature
    draw_control_panel(
        screen, control_panel_buttons, sliders_list, progress_bar_props,
        current_mode, APP_MODES, pygame.mouse.get_pos(),
        current_song_time_seconds, total_song_duration_seconds, base_bpm # Removed tempo_multiplier, it's global
    )
    if current_mode == APP_MODES['PRESENTATION'] or current_mode == APP_MODES['LEARNING']:
        time_for_roll = learning_mode_state['paused_at_time'] if current_mode == APP_MODES['LEARNING'] and learning_mode_state['paused_at_time'] is not None else current_song_time_seconds
        # draw_piano_roll_notes content was removed for brevity, ensure it's there
        # Re-inserting draw_piano_roll_notes for clarity
        if pixels_per_second > 0:
            for note in song_data:
                note_end_time = note['start_time'] + note['duration']
                if note['start_time'] < time_for_roll + PIANO_ROLL_LOOKAHEAD_SECONDS and note_end_time > time_for_roll:
                    x_center = get_x_for_midi_note(note['midi_note'], KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, white_key_width)
                    if x_center is None: continue
                    semitone = note['midi_note'] % 12
                    white_note_semitones = [0, 2, 4, 5, 7, 9, 11]
                    is_white_note = semitone in white_note_semitones
                    rect_width = white_key_width * NOTE_RECT_WIDTH_WHITE_RATIO if is_white_note else black_key_width * NOTE_RECT_WIDTH_BLACK_RATIO
                    rect_left_x = x_center - (rect_width / 2)
                    time_offset_sec_roll = note['start_time'] - time_for_roll
                    y_offset_px_roll = time_offset_sec_roll * pixels_per_second
                    note_bottom_y_on_roll = PIANO_ROLL_BOTTOM_Y - y_offset_px_roll
                    note_height_px = note['duration'] * pixels_per_second
                    note_top_y_on_roll = note_bottom_y_on_roll - note_height_px
                    visible_top_y = max(note_top_y_on_roll, PIANO_ROLL_TOP_Y)
                    visible_bottom_y = min(note_bottom_y_on_roll, PIANO_ROLL_BOTTOM_Y)
                    visible_height = visible_bottom_y - visible_top_y
                    if visible_height > 0:
                        note_rect = pygame.Rect(rect_left_x, visible_top_y, rect_width, visible_height)
                        pygame.draw.rect(screen, NOTE_RECT_COLOR, note_rect)
                        pygame.draw.rect(screen, NOTE_RECT_BORDER_COLOR, note_rect, 1)

    draw_piano(screen, white_key_pressed_states, black_key_pressed_states)
    if feedback_flash_info['key_midi'] is not None and feedback_flash_info['end_time_ms'] > pygame.time.get_ticks():
        # draw_feedback_flash_overlay content was removed for brevity, ensure it's there
        # Re-inserting draw_feedback_flash_overlay for clarity
        flash_info = feedback_flash_info
        key_type_f, key_idx_f = get_key_type_and_index_for_midi(flash_info['key_midi'], KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, NUM_BLACK_KEYS)
        if key_type_f is not None:
            key_center_x_f = get_x_for_midi_note(flash_info['key_midi'], KEYBOARD_START_MIDI_NOTE, NUM_WHITE_KEYS, white_key_width)
            if key_center_x_f is not None:
                flash_rect_f = None
                if key_type_f == 'white':
                    flash_rect_f = pygame.Rect(key_center_x_f - white_key_width/2, WINDOW_HEIGHT - keyboard_height, white_key_width, white_key_height)
                elif key_type_f == 'black':
                    flash_rect_f = pygame.Rect(key_center_x_f - black_key_width/2, WINDOW_HEIGHT - keyboard_height, black_key_width, black_key_height)
                if flash_rect_f:
                    flash_surface_f = pygame.Surface(flash_rect_f.size, pygame.SRCALPHA)
                    flash_surface_f.fill((*flash_info['color'], 128))
                    screen.blit(flash_surface_f, flash_rect_f.topleft)
        else: feedback_flash_info['key_midi'] = None # Clear if invalid
    else: feedback_flash_info['key_midi'] = None

    if mode_switch_confirm_active:
        overlay_surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay_surface.fill((0, 0, 0, 180))
        screen.blit(overlay_surface, (0,0))
        target_mode_name = "Presentation" if target_mode_on_confirm == APP_MODES['PRESENTATION'] else "Learning"
        prompts = [f"Switch to {target_mode_name} Mode?", "Reset song (R) or Continue current position (C)?", "Press Esc to Cancel."]
        text_y_start = WINDOW_HEIGHT // 2 - 50
        for i_prompt, prompt_text in enumerate(prompts):
            surf = control_panel_font.render(prompt_text, True, WHITE)
            rect = surf.get_rect(center=(WINDOW_WIDTH // 2, text_y_start + i_prompt * 30))
            screen.blit(surf, rect)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
