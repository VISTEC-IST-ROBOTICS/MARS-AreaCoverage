import pygame
import pygame_gui

pygame.init()
WINDOW_SIZE = (800, 600)
screen = pygame.display.set_mode(WINDOW_SIZE)
pygame.display.set_caption("Pygame GUI File Menu Example")
clock = pygame.time.Clock()

# Create the UI manager
manager = pygame_gui.UIManager(WINDOW_SIZE)

# Top ribbon background
top_bar = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((0, 0), (WINDOW_SIZE[0], 40)),
    manager=manager,
    anchors={'top': 'top', 'left': 'left', 'right': 'right'}
)


# File menu button on ribbon
file_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((10, 5), (80, 30)),
    text='File',
    manager=manager,
    container=top_bar
)

# Dropdown menu panel (hidden by default)
file_menu_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect((10, 40), (120, 100)),
    manager=manager,
    visible=0
)

# Dropdown options
open_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((5, 5), (110, 30)),
    text='Open',
    manager=manager,
    container=file_menu_panel
)
save_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((5, 35), (110, 30)),
    text='Save',
    manager=manager,
    container=file_menu_panel
)
quit_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect((5, 65), (110, 30)),
    text='Quit',
    manager=manager,
    container=file_menu_panel
)

running = True
while running:
    time_delta = clock.tick(60) / 1000
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Handle clicks
        if event.type == pygame.USEREVENT and event.user_type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == file_button:
                file_menu_panel.show()

            elif event.ui_element == open_button:
                print("Open clicked")
                file_menu_panel.hide()

            elif event.ui_element == save_button:
                print("Save clicked")
                file_menu_panel.hide()

            elif event.ui_element == quit_button:
                running = False

        # Hide dropdown if clicked outside
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            if not file_menu_panel.get_relative_rect().collidepoint(mouse_pos) and not file_button.rect.collidepoint(mouse_pos):
                file_menu_panel.hide()

        manager.process_events(event)

    manager.update(time_delta)
    screen.fill((230, 230, 230))
    manager.draw_ui(screen)
    pygame.display.update()

pygame.quit()
