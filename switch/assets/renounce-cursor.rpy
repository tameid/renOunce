# Switch 2 Joy-Con mouse: translate libounce's PadPointer into Ren'Py input.
init -100 python:
    if renpy.switch:
        import _otrhlibnx
        import pygame_sdl2 as pygame

        renounce_mouse_active = False
        renounce_mouse_buttons = 0
        renounce_mouse_pos = None
        renounce_mouse_armed = False
        renounce_last_tracking = 0
        renounce_fast_timer = False

        # Ren'Py normally polls at 20 Hz. Match the display refresh for the
        # Joy-Con pointer while keeping the engine's ordinary periodic loop.
        renpy.display.core.PERIODIC_INTERVAL = 16

        class RenounceMouseDisplayable(MouseDisplayable):
            def render(self, width, height, st, at):
                if not renounce_mouse_active:
                    return renpy.Render(width, height)
                return MouseDisplayable.render(self, width, height, st, at)

        renounce_pointer = RenounceMouseDisplayable("_renounce_cursor.png", 0, 0)
        config.mouse_displayable = renounce_pointer
        config.mouse_hide_time = None

        def renounce_poll_mouse():
            global renounce_mouse_active, renounce_mouse_buttons, renounce_mouse_pos
            global renounce_mouse_armed, renounce_last_tracking, renounce_fast_timer
            if not renounce_fast_timer:
                pygame.time.set_timer(renpy.display.core.PERIODIC, 16)
                renounce_fast_timer = True
            surface = pygame.display.get_surface()
            if surface is None:
                return

            pointer_active, x, y, buttons, wheel, tracking, moved = _otrhlibnx.polljoyconmouse(*surface.get_size())
            now = pygame.time.get_ticks()
            if not pointer_active:
                renounce_mouse_armed = False
                renounce_last_tracking = 0
            elif tracking:
                renounce_last_tracking = now
                if moved:
                    renounce_mouse_armed = True

            # Detaching a Joy-Con exposes an Nmouse handle even before its
            # optical sensor is against a surface. Require tracked movement
            # to enter mouse mode; tolerate brief missing samples on lift.
            active = bool(pointer_active and renounce_mouse_armed and
                          now - renounce_last_tracking <= 200)
            pos = (x, y)

            if active and pos != renounce_mouse_pos:
                pygame.mouse.set_pos(pos)
                renounce_mouse_pos = pos
                renpy.redraw(renounce_pointer, 0)

            for mask, button in ((1, 1), (2, 3), (4, 2)):
                was_down = bool(renounce_mouse_buttons & mask)
                is_down = active and bool(buttons & mask)
                if was_down != is_down:
                    kind = pygame.MOUSEBUTTONDOWN if is_down else pygame.MOUSEBUTTONUP
                    pygame.event.post(pygame.event.Event(kind, {"button": button, "pos": pos}))

            if active and wheel:
                button = 4 if wheel > 0 else 5
                for i in range(min(abs(wheel), 8)):
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": button, "pos": pos}))
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": button, "pos": pos}))

            renounce_mouse_buttons = buttons if active else 0
            if active != renounce_mouse_active:
                renounce_mouse_active = active
                renpy.redraw(renounce_pointer, 0)

        config.periodic_callbacks.append(renounce_poll_mouse)
