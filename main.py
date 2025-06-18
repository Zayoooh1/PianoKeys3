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

# --- Piano Roll Constants ---
PIANO_ROLL_LOOKAHEAD_SECONDS = 5.0  # How far ahead in time notes are prepared/visible conceptually
PIANO_ROLL_SECONDS_ON_SCREEN = 5.0  # How many seconds of notes are visible vertically on the roll display area
PIANO_ROLL_TOP_Y = 50               # Y-coordinate for the top of the piano roll display area
# keyboard_height is already defined, ensure it's accessible here
PIANO_ROLL_BOTTOM_Y = WINDOW_HEIGHT - keyboard_height - 10 # Y-coordinate for where notes "hit" the keyboard line
NOTE_RECT_COLOR = (0, 150, 255)     # A modern blue/teal for note rectangles
NOTE_RECT_BORDER_COLOR = (200, 200, 255) # Border for note rectangles
NOTE_RECT_WIDTH_WHITE_RATIO = 0.8 # Proportion of white key width for the note rectangle
NOTE_RECT_WIDTH_BLACK_RATIO = 0.9 # Proportion of black key width for the note rectangle


# Calculate pixels_per_second based on the defined screen area and time visible
# Ensure PIANO_ROLL_BOTTOM_Y > PIANO_ROLL_TOP_Y to avoid division by zero or negative
if PIANO_ROLL_BOTTOM_Y > PIANO_ROLL_TOP_Y and PIANO_ROLL_SECONDS_ON_SCREEN > 0:
    pixels_per_second = (PIANO_ROLL_BOTTOM_Y - PIANO_ROLL_TOP_Y) / PIANO_ROLL_SECONDS_ON_SCREEN
else:
    pixels_per_second = 0 # Avoid error, but piano roll will not work correctly
    print("Warning: Piano roll Y coordinates or seconds_on_screen are configured incorrectly.")

# Pressed State Lists
NUM_BLACK_KEYS = 5 * OCTAVES # Standard 5 black keys per octave
white_key_pressed_states = [False] * NUM_WHITE_KEYS
black_key_pressed_states = [False] * NUM_BLACK_KEYS

SOUNDS_DIR = "sounds"
PLACEHOLDER_SOUND = os.path.join(SOUNDS_DIR, "placeholder.wav")

# Create sounds directory if it doesn't exist
if not os.path.exists(SOUNDS_DIR):
    os.makedirs(SOUNDS_DIR)

# PC key to piano key mapping
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

# Load sounds
for key_code, key_data in key_map.items():
    try:
        # This will fail if placeholder.wav doesn't exist yet,
        # but the structure is what we want.
        # The actual file creation is a later plan step.
        sound = pygame.mixer.Sound(key_data['sound_file'])
        key_data['sound_obj'] = sound
    except pygame.error as e:
        print(f"Could not load sound for key {pygame.key.name(key_code)}: {key_data['sound_file']} - {e}")
        # Keep sound_obj as None if loading fails

# --- MIDI to Sound Object Mapping ---
midi_to_sound_map = {}

# Define the starting MIDI note of our virtual keyboard (e.g., C4 = 60)
# This must match the assumption used when building key_map earlier.
# If key_map's white key index 0 is C4, black key index 0 is C#4 etc.
KEYBOARD_START_MIDI_NOTE = 60 # C4

# MIDI offsets from C for white keys: C, D, E, F, G, A, B
WHITE_KEY_MIDI_OFFSETS = [0, 2, 4, 5, 7, 9, 11]
# MIDI offsets from C for black keys: C#, D#, F#, G#, A#
BLACK_KEY_MIDI_OFFSETS = [1, 3, 6, 8, 10] # Relative to C of the octave

# Populate midi_to_sound_map by iterating through key_map
for pc_key, data in key_map.items():
    key_type = data['type']
    key_index_on_keyboard = data['index'] # This is the 0-9 for white, 0-6 for black as per key_map
    sound_obj = data['sound_obj']

    if sound_obj: # Only map if sound was loaded
        midi_note = -1
        # octave_offset = (key_index_on_keyboard // 7) if key_type == 'white' else (key_index_on_keyboard // 5)

        if key_type == 'white':
            # key_index_on_keyboard for white keys in key_map goes from 0 to NUM_WHITE_KEYS-1 (e.g. 0-13 for 2 octaves)
            # Octave for C4 is KEYBOARD_START_MIDI_NOTE // 12
            octave_num = (KEYBOARD_START_MIDI_NOTE // 12) + (key_index_on_keyboard // 7) # White keys per octave is 7
            offset_in_octave = WHITE_KEY_MIDI_OFFSETS[key_index_on_keyboard % 7]
            midi_note = octave_num * 12 + offset_in_octave

        elif key_type == 'black':
            # key_index_on_keyboard for black keys in key_map goes from 0 to NUM_BLACK_KEYS-1 (e.g. 0-9 for 2 octaves)
            # Black keys per octave is 5
            octave_num = (KEYBOARD_START_MIDI_NOTE // 12) + (key_index_on_keyboard // 5)
            offset_in_octave = BLACK_KEY_MIDI_OFFSETS[key_index_on_keyboard % 5]
            midi_note = octave_num * 12 + offset_in_octave

        if midi_note != -1:
            if midi_note not in midi_to_sound_map: # Avoid overwriting if multiple PC keys map to same sound
                midi_to_sound_map[midi_note] = sound_obj
            # print(f"Mapped MIDI {midi_note} to sound from PC key {pygame.key.name(pc_key)}")

# print("MIDI to Sound Map:", midi_to_sound_map) # For debugging


# --- Song Data ---
# Structure: {'midi_note': int, 'start_time': float, 'duration': float, 'played': False}
# MIDI notes for "Wlazł kotek na płotek" (approximate)
# G4: 67, E4: 64, C4: 60, A4: 69

song_data = [
    # Wlazł ko-tek na płotek
    # G E C G A G E C (notes)
    # 1 2 3 4 5 6 7 8 (syllables for timing)
    {'midi_note': 67, 'start_time': 0.0, 'duration': 0.4, 'played': False},  # Wlazł (G4)
    {'midi_note': 64, 'start_time': 0.5, 'duration': 0.4, 'played': False},  # ko- (E4)
    {'midi_note': 60, 'start_time': 1.0, 'duration': 0.4, 'played': False},  # -tek (C4)

    {'midi_note': 67, 'start_time': 1.5, 'duration': 0.4, 'played': False},  # na (G4)
    {'midi_note': 69, 'start_time': 2.0, 'duration': 0.4, 'played': False},  # pło- (A4)
    {'midi_note': 67, 'start_time': 2.5, 'duration': 0.4, 'played': False},  # -tek (G4)

    {'midi_note': 64, 'start_time': 3.0, 'duration': 0.4, 'played': False},  # i (E4)
    {'midi_note': 60, 'start_time': 3.5, 'duration': 0.4, 'played': False},  # mru- (C4)
    # For "mruga", the last note often goes up or resolves. Let's use G4 for simplicity.
    {'midi_note': 67, 'start_time': 4.0, 'duration': 0.4, 'played': False},  # -ga (G4)
]

def debug_print_song(notes_list):
    print("--- Song Debug Print ---")
    if not notes_list:
        print("No notes in the song.")
        return
    for i, note_info in enumerate(notes_list):
        print(f"Note {i+1}: MIDI={note_info.get('midi_note', 'N/A')}, "
              f"Start={note_info.get('start_time', 'N/A'):.2f}s, "
              f"Duration={note_info.get('duration', 'N/A'):.2f}s, "
              f"Played={note_info.get('played', 'N/A')}")
    print("------------------------")

# Example of how to call it (optional, can be commented out):
# If you want to test it immediately when the script runs:
# debug_print_song(song_data)

# --- Presentation Mode State and Timing ---
presentation_mode_active = True  # Set to True for initial testing
current_song_time_seconds = 0.0
song_start_time_ticks = 0 # Stores pygame.time.get_ticks() when the song playback begins

# Function to reset song played states (call before starting presentation mode)
def reset_song_played_states(notes_list):
    for note_info in notes_list:
        note_info['played'] = False

# Initially reset the song data if presentation mode is active from the start
if presentation_mode_active:
    reset_song_played_states(song_data) # song_data should be defined before this

def get_x_for_midi_note(midi_note, first_midi_note_on_keyboard, num_total_white_keys, white_key_width_px):
    """
    Calculates the X-coordinate for the center of a given MIDI note on the virtual keyboard.

    Args:
        midi_note: The MIDI note number (e.g., C4=60).
        first_midi_note_on_keyboard: MIDI note of the first key (leftmost) on our keyboard.
                                      (Assuming our keyboard starts on a C, e.g. C4 = 60 for a 2-octave C-C keyboard)
        num_total_white_keys: Total number of white keys on the keyboard (e.g., 14 for 2 octaves).
        white_key_width_px: Width of a single white key in pixels.
    Returns:
        The X-coordinate for the center of the note, or None if note is out of range.
    """
    # Determine the note's position relative to C. C=0, C#=1, ..., B=11
    # note_offset_from_c = midi_note % 12 # This is semitone
    # octave_number = midi_note // 12 # This is octave

    # Define which relative notes are "white" (0=C, 2=D, 4=E, 5=F, 7=G, 9=A, 11=B)
    white_note_positions_in_octave = [0, 2, 4, 5, 7, 9, 11]

    # Position of the note within the 12-semitone system (0=C, 1=C#, ..., 11=B)
    semitone = midi_note % 12
    # Octave of the note (e.g., C4 is octave 4 if using middle C=60 as reference, but MIDI lib might use 5)
    octave = midi_note // 12

    # MIDI note of C in the same octave as the target note
    # c_of_octave = octave * 12 # Not directly used but good for understanding

    # Number of white keys from C up to the semitone (inclusive if semitone is white)
    # C(0,wk0), D(2,wk1), E(4,wk2), F(5,wk3), G(7,wk4), A(9,wk5), B(11,wk6)
    # white_key_map maps a semitone (0-11) to its corresponding white key index (0-6) within that octave.
    # For black keys, it maps to the white key immediately to its left.
    white_key_map = {0:0, 1:0, 2:1, 3:1, 4:2, 5:3, 6:3, 7:4, 8:4, 9:5, 10:5, 11:6}

    white_key_num_in_octave = white_key_map[semitone]

    # Assume first_midi_note_on_keyboard is C4 (60) for a 2-octave C4-B5 keyboard
    # Octave of the first key on our keyboard
    base_octave = first_midi_note_on_keyboard // 12

    # Overall white key index from the start of our keyboard
    total_white_key_index = (octave - base_octave) * 7 + white_key_num_in_octave

    if not (0 <= total_white_key_index < num_total_white_keys):
        # print(f"Note {midi_note} is outside the keyboard range {first_midi_note_on_keyboard} - {first_midi_note_on_keyboard + num_total_white_keys*12/7 }. Actual white keys {num_total_white_keys}")
        return None # Note is outside the keyboard range

    x_coord = 0
    if semitone not in white_note_positions_in_octave: # It's a black key
        # Black keys are centered over the division line between the white key they
        # are associated with (to their left) and the next white key.
        # total_white_key_index gives the white key to the left (e.g., C for C#).
        # The line is at the end of this white key.
        x_coord = (total_white_key_index + 1) * white_key_width_px
    else: # It's a white key
        # Center of the white key
        x_coord = (total_white_key_index * white_key_width_px) + (white_key_width_px / 2.0)

    return x_coord

# Example: For a 2-octave keyboard starting at C4 (MIDI 60)
# NUM_WHITE_KEYS is 14 (defined globally)
# white_key_width is also global
# So the call might look like:
# get_x_for_midi_note(midi_note, 60, NUM_WHITE_KEYS, white_key_width)
# Ensure global `black_key_width` is accessible if used as above.

def get_key_type_and_index_for_midi(midi_note, first_midi_note_on_keyboard, num_total_white_keys, num_total_black_keys):
    """
    Determines the type ('white' or 'black') and index (0-based) of a piano key
    corresponding to a given MIDI note, relative to our specific virtual keyboard.

    Args:
        midi_note: The MIDI note number.
        first_midi_note_on_keyboard: MIDI note of the first key on our keyboard (e.g., C4=60).
        num_total_white_keys: Total number of white keys on this keyboard.
        num_total_black_keys: Total number of black keys on this keyboard.

    Returns:
        A tuple (key_type, key_index) e.g., ('white', 0) or ('black', 3),
        or (None, None) if the note is out of range or cannot be mapped.
    """
    semitone = midi_note % 12  # Note relative to C (C=0, C#=1, ..., B=11)
    octave = midi_note // 12

    base_octave = first_midi_note_on_keyboard // 12

    # MIDI offsets from C for white keys: C, D, E, F, G, A, B
    white_note_semitones_in_octave = [0, 2, 4, 5, 7, 9, 11]
    # Map semitone to white key index within an octave (0-6)
    white_key_indices_map = {0:0, 1:0, 2:1, 3:1, 4:2, 5:3, 6:3, 7:4, 8:4, 9:5, 10:5, 11:6}
    # Map semitone to black key index within an octave (0-4 for C#,D#,F#,G#,A#)
    black_key_indices_map = {1:0, 3:1, 6:2, 8:3, 10:4} # Keys are C#, D#, F#, G#, A#


    if semitone in white_note_semitones_in_octave:
        key_type = 'white'
        # White key index within its octave (0 for C, 1 for D, ..., 6 for B)
        idx_in_octave = white_key_indices_map[semitone]
        # Overall white key index from the start of our keyboard
        key_index = (octave - base_octave) * 7 + idx_in_octave # 7 white keys per octave
        if not (0 <= key_index < num_total_white_keys):
            return None, None # Out of range for this keyboard
    elif semitone in black_key_indices_map:
        key_type = 'black'
        # Black key index within its octave (0 for C#, 1 for D#, ..., 4 for A#)
        idx_in_octave = black_key_indices_map[semitone]
        # Overall black key index from the start of our keyboard
        key_index = (octave - base_octave) * 5 + idx_in_octave # 5 black keys per octave
        if not (0 <= key_index < num_total_black_keys):
            return None, None # Out of range for this keyboard
    else:
        # This case should ideally not be reached if midi_note is a valid piano note.
        return None, None

    return key_type, key_index

# Constants like NUM_WHITE_KEYS and NUM_BLACK_KEYS (total on our keyboard)
# and KEYBOARD_START_MIDI_NOTE (e.g., 60) will be passed to this.

def draw_piano_roll_notes(surface, current_time_sec, notes_list, px_per_sec,
                          lookahead_sec, first_midi_ref, total_white_keys_ref, white_key_w_ref, black_key_w_ref):
    """
    Draws the falling notes for the piano roll.
    Args:
        surface: Pygame surface to draw on.
        current_time_sec: Current playback time in the song.
        notes_list: The list of song notes (e.g., song_data).
        px_per_sec: Vertical pixels representing one second of time in the roll.
        lookahead_sec: How many seconds into the future notes should be considered for drawing.
        first_midi_ref: MIDI note of the first key on keyboard (for get_x_for_midi_note).
        total_white_keys_ref: Total white keys on keyboard (for get_x_for_midi_note).
        white_key_w_ref: Width of a white key (for get_x_for_midi_note and note rect width).
        black_key_w_ref: Width of a black key (for note rect width).
    """
    if px_per_sec <= 0: # Avoid division by zero or incorrect drawing if scale is bad
        return

    for note in notes_list:
        # Only draw notes that are upcoming or currently active within the lookahead window
        # Also, only draw notes that haven't been marked 'played' if we want them to disappear after playing
        # current_time_sec - note['duration'] < note['start_time'] < current_time_sec + lookahead_sec

        # Condition to draw: Note is active now OR will be active soon (within lookahead)
        # AND note hasn't finished yet more than a moment ago (e.g., current_time < note_end_time + grace_period)
        # Simplified: Draw if note is (start_time to end_time) overlaps with (current_time to current_time + lookahead_sec)
        # A note is relevant if:
        #   note_start_time < current_time_sec + lookahead_sec  (it starts before the lookahead window ends)
        #   AND note_end_time > current_time_sec                (it ends after the current moment)
        note_end_time = note['start_time'] + note['duration']
        if note['start_time'] < current_time_sec + lookahead_sec and note_end_time > current_time_sec:

            x_center = get_x_for_midi_note(note['midi_note'], first_midi_ref, total_white_keys_ref, white_key_w_ref)
            if x_center is None: # Note is out of keyboard range
                continue

            # Determine if the note is white or black for width calculation
            semitone = note['midi_note'] % 12
            white_note_semitones = [0, 2, 4, 5, 7, 9, 11] # C, D, E, F, G, A, B
            is_white_note = semitone in white_note_semitones

            rect_width = 0
            if is_white_note:
                rect_width = white_key_w_ref * NOTE_RECT_WIDTH_WHITE_RATIO
            else:
                # For black keys, use black_key_width (which is global)
                rect_width = black_key_w_ref * NOTE_RECT_WIDTH_BLACK_RATIO

            rect_left_x = x_center - (rect_width / 2)

            # Y-positioning
            # note_bottom_y is where the note's start_time aligns with the "hit" line (PIANO_ROLL_BOTTOM_Y)
            # If note['start_time'] == current_time_sec, then note_bottom_y should be PIANO_ROLL_BOTTOM_Y.
            # If note['start_time'] > current_time_sec (future note), it's higher up (smaller Y).
            # If note['start_time'] < current_time_sec (past note, still sounding), it's lower (larger Y).

            # Position of the bottom of the note rectangle relative to PIANO_ROLL_BOTTOM_Y
            # when current_time_sec matches note['start_time'], this offset is 0.
            time_offset_sec = note['start_time'] - current_time_sec
            y_offset_px = time_offset_sec * px_per_sec

            note_bottom_y_on_roll = PIANO_ROLL_BOTTOM_Y - y_offset_px
            note_height_px = note['duration'] * px_per_sec
            note_top_y_on_roll = note_bottom_y_on_roll - note_height_px

            # Clip notes that are partially above or below the piano roll viewing area
            # Top of visible rect is the max of note's actual top and the piano roll's top boundary
            visible_top_y = max(note_top_y_on_roll, PIANO_ROLL_TOP_Y)
            # Bottom of visible rect is the min of note's actual bottom and the piano roll's bottom boundary
            visible_bottom_y = min(note_bottom_y_on_roll, PIANO_ROLL_BOTTOM_Y)

            visible_height = visible_bottom_y - visible_top_y

            if visible_height > 0: # Only draw if there's a visible part
                note_rect = pygame.Rect(rect_left_x, visible_top_y, rect_width, visible_height)
                pygame.draw.rect(surface, NOTE_RECT_COLOR, note_rect)
                pygame.draw.rect(surface, NOTE_RECT_BORDER_COLOR, note_rect, 1)

# Note: white_key_pressed_states and black_key_pressed_states are now passed as arguments
def draw_white_key(surface, rect, shadow_offset, is_pressed):
    """Draws a white piano key with a shadow, changing appearance if pressed."""
    current_fill_color = WHITE
    if is_pressed:
        current_fill_color = GRAY # Change color when pressed
        pygame.draw.rect(surface, current_fill_color, rect)
        pygame.draw.rect(surface, BLACK, rect, 1) # Border
    else:
        # Original shadow drawing logic
        shadow_rect = rect.move(shadow_offset, shadow_offset)
        pygame.draw.rect(surface, GRAY, shadow_rect)
        pygame.draw.rect(surface, current_fill_color, rect)
        pygame.draw.rect(surface, BLACK, rect, 2) # Border

def draw_black_key(surface, rect, shadow_offset, is_pressed):
    """Draws a black piano key with a shadow, changing appearance if pressed."""
    current_fill_color = BLACK
    if is_pressed:
        current_fill_color = LIGHTER_GRAY # Change color when pressed
        pygame.draw.rect(surface, current_fill_color, rect)
    else:
        # Original shadow drawing logic
        shadow_rect = rect.move(shadow_offset, shadow_offset)
        pygame.draw.rect(surface, (150,150,150), shadow_rect)
        pygame.draw.rect(surface, current_fill_color, rect)

def draw_piano(surface, white_pressed_states, black_pressed_states):
    # Calculate Keyboard Position
    keyboard_y_start = WINDOW_HEIGHT - white_key_height

    # Draw White Keys
    for i in range(NUM_WHITE_KEYS):
        white_key_x = i * white_key_width
        white_key_rect = pygame.Rect(white_key_x, keyboard_y_start, white_key_width, white_key_height)
        draw_white_key(surface, white_key_rect, SHADOW_OFFSET, white_key_pressed_states[i])

    # Draw Black Keys
    # Pattern for black keys in one octave (True if black key follows the white key)
    # C# D# (skip E-F) F# G# A# (skip B-C)
    # Indices: 0  1    2    3  4  5    6
    black_key_pattern = [True, True, False, True, True, True, False]
    black_key_idx_counter = 0 # To index into black_key_pressed_states

    for i in range(NUM_WHITE_KEYS):
        # Check pattern for the current octave
        if black_key_pattern[i % 7]:
            # Also ensure we are not trying to draw a black key past the last white key's area
            if i < NUM_WHITE_KEYS -1: # Check to avoid drawing black key beyond the last white key
                if black_key_idx_counter < NUM_BLACK_KEYS: # Ensure we don't go out of bounds for pressed states
                    black_key_x = (i + 1) * white_key_width - (black_key_width // 2)
                    black_key_rect = pygame.Rect(black_key_x, keyboard_y_start, black_key_width, black_key_height)
                    # Use black_key_idx_counter for black_key_pressed_states
                    draw_black_key(surface, black_key_rect, SHADOW_OFFSET, black_key_pressed_states[black_key_idx_counter])
                    black_key_idx_counter += 1
                else: # Should not happen if NUM_BLACK_KEYS is correct
                    print(f"Warning: Attempting to draw more black keys than defined by NUM_BLACK_KEYS ({NUM_BLACK_KEYS})")

# Initialize Clock
clock = pygame.time.Clock()

# Reset song start time if presentation mode is active
if presentation_mode_active:
    song_start_time_ticks = 0 # Will be set on first frame of presentation
    # reset_song_played_states(song_data) # This is already done when presentation_mode_active is set earlier

# Game Loop
running = True
while running:
    # Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN and not presentation_mode_active: # Only process key presses if not in presentation mode
            if event.key in key_map:
                mapped_key = key_map[event.key]
                key_type = mapped_key['type']
                key_index = mapped_key['index']

                if key_type == 'white':
                    if 0 <= key_index < len(white_key_pressed_states):
                        white_key_pressed_states[key_index] = True
                elif key_type == 'black':
                    if 0 <= key_index < len(black_key_pressed_states):
                        black_key_pressed_states[key_index] = True

                # Play sound
                if mapped_key['sound_obj']:
                    mapped_key['sound_obj'].play()

        if event.type == pygame.KEYUP:
            if event.key in key_map:
                mapped_key = key_map[event.key]
                key_type = mapped_key['type']
                key_index = mapped_key['index']

                if key_type == 'white':
                    if 0 <= key_index < len(white_key_pressed_states):
                        white_key_pressed_states[key_index] = False
                elif key_type == 'black':
                    if 0 <= key_index < len(black_key_pressed_states):
                        black_key_pressed_states[key_index] = False

    if presentation_mode_active:
        if song_start_time_ticks == 0: # First frame in presentation mode
            song_start_time_ticks = pygame.time.get_ticks()
            # Ensure song states are fresh if mode was toggled at runtime later
            reset_song_played_states(song_data)


        current_song_time_seconds = (pygame.time.get_ticks() - song_start_time_ticks) / 1000.0

        # Process notes for automatic playing and key release
        for note_info in song_data:
            key_type, key_idx = get_key_type_and_index_for_midi(
                note_info['midi_note'],
                KEYBOARD_START_MIDI_NOTE,
                NUM_WHITE_KEYS,
                NUM_BLACK_KEYS
            )

            if key_type is None: # Note is not on our keyboard
                continue

            # Check for note activation
            if not note_info['played'] and note_info['start_time'] <= current_song_time_seconds:
                if key_type == 'white':
                    if 0 <= key_idx < NUM_WHITE_KEYS:
                        white_key_pressed_states[key_idx] = True
                elif key_type == 'black':
                    if 0 <= key_idx < NUM_BLACK_KEYS:
                        black_key_pressed_states[key_idx] = True

                # Play sound
                if note_info['midi_note'] in midi_to_sound_map and midi_to_sound_map[note_info['midi_note']]:
                    midi_to_sound_map[note_info['midi_note']].play()

                note_info['played'] = True # Mark as played (triggered)

            # Check for note deactivation (release)
            note_end_time = note_info['start_time'] + note_info['duration']
            if note_info['played'] and note_end_time <= current_song_time_seconds:
                # Only release if the key is currently shown as pressed by this logic.
                # This is a simple check; more robust state tracking might be needed for complex scenarios.
                key_is_pressed_by_presenter = False
                if key_type == 'white' and 0 <= key_idx < NUM_WHITE_KEYS and white_key_pressed_states[key_idx]:
                     # Check if this key was the one most recently activated for this note_info if multiple notes map to it
                    key_is_pressed_by_presenter = True # Simplified: assume it was this note
                elif key_type == 'black' and 0 <= key_idx < NUM_BLACK_KEYS and black_key_pressed_states[key_idx]:
                    key_is_pressed_by_presenter = True # Simplified

                if key_is_pressed_by_presenter:
                    if key_type == 'white':
                        white_key_pressed_states[key_idx] = False
                    elif key_type == 'black':
                        black_key_pressed_states[key_idx] = False
                    # Consider adding a 'released_by_presenter' flag to note_info if needed
                    # to prevent this from running multiple times or interfering with user playing same note.
                    # For now, 'played' being true covers this.

    # Drawing
    screen.fill(BACKGROUND_COLOR)

    if presentation_mode_active:
        draw_piano_roll_notes(
            screen,
            current_song_time_seconds,
            song_data,
            pixels_per_second,
            PIANO_ROLL_LOOKAHEAD_SECONDS,
            KEYBOARD_START_MIDI_NOTE,
            NUM_WHITE_KEYS,
            white_key_width,
            black_key_width
        )

    draw_piano(screen, white_key_pressed_states, black_key_pressed_states)

    # Update Display
    pygame.display.flip()

    # Control Frame Rate
    clock.tick(30)

# Quit Pygame
pygame.quit()
sys.exit()
