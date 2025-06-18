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

# Game Loop
running = True
while running:
    # Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
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

    # Drawing
    screen.fill(BACKGROUND_COLOR)
    draw_piano(screen, white_key_pressed_states, black_key_pressed_states)

    # Update Display
    pygame.display.flip()

    # Control Frame Rate
    clock.tick(30)

# Quit Pygame
pygame.quit()
sys.exit()
