import pygame
import sys

# Initialize Pygame
pygame.init()

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

def draw_white_key(surface, rect, shadow_offset):
    """Draws a white piano key with a shadow."""
    shadow_rect = pygame.Rect(rect.x + shadow_offset, rect.y + shadow_offset, rect.width, rect.height)
    pygame.draw.rect(surface, GRAY, shadow_rect)  # Draw shadow
    pygame.draw.rect(surface, WHITE, rect)  # Draw key
    pygame.draw.rect(surface, BLACK, rect, 2)  # Draw border

def draw_black_key(surface, rect, shadow_offset):
    """Draws a black piano key with a shadow."""
    shadow_rect = pygame.Rect(rect.x + shadow_offset, rect.y + shadow_offset, rect.width, rect.height)
    pygame.draw.rect(surface, (150, 150, 150), shadow_rect)  # Draw shadow
    pygame.draw.rect(surface, BLACK, rect)  # Draw key

def draw_piano(surface):
    # Calculate Keyboard Position
    keyboard_y_start = WINDOW_HEIGHT - white_key_height

    # Draw White Keys
    for i in range(NUM_WHITE_KEYS):
        white_key_x = i * white_key_width
        white_key_rect = pygame.Rect(white_key_x, keyboard_y_start, white_key_width, white_key_height)
        draw_white_key(surface, white_key_rect, SHADOW_OFFSET)

    # Draw Black Keys
    # Pattern for black keys in one octave (True if black key follows the white key)
    # C# D# (skip E-F) F# G# A# (skip B-C)
    # Indices: 0  1    2    3  4  5    6
    black_key_pattern = [True, True, False, True, True, True, False]

    for i in range(NUM_WHITE_KEYS):
        # Check pattern for the current octave
        if black_key_pattern[i % 7]:
            # Also ensure we are not trying to draw a black key past the last white key's area
            if i < NUM_WHITE_KEYS -1: # Check to avoid drawing black key beyond the last white key
                black_key_x = (i + 1) * white_key_width - (black_key_width // 2)
                black_key_rect = pygame.Rect(black_key_x, keyboard_y_start, black_key_width, black_key_height)
                draw_black_key(surface, black_key_rect, SHADOW_OFFSET)

# Initialize Clock
clock = pygame.time.Clock()

# Game Loop
running = True
while running:
    # Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Drawing
    screen.fill(BACKGROUND_COLOR)
    draw_piano(screen)

    # Update Display
    pygame.display.flip()

    # Control Frame Rate
    clock.tick(30)

# Quit Pygame
pygame.quit()
sys.exit()
