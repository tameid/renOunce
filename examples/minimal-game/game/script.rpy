# renOunce demo game.
#
# Deliberately uses only what ships in renpy/common (no project gui, no
# assets), so it boots on real hardware with zero extras and doubles as the
# CI probe for the per-game NRO pipeline:
#   - text pages prove rendering (GLES via OunceVK/Zink) came up,
#   - the final utter_restart proves appletRestartProgram works from an NRO
#     (PLAN.md §8.1),
#   - this build is branded "renOunce Demo" and saves/logs land in
#     sdmc:/renOunce/renOunceDemo/ — a folder no other game uses.

define demo.pages = [
    "This NRO was built by renOunce.",
    "If you can read this on the Switch 2, the whole pipeline worked.",
    "Saves, logs and cache for this game live in",
    "sdmc:/renOunce/renOunce_Demo/",
    "Restarting, to prove appletRestartProgram works from an NRO...",
    ]

label start:

    $ n = 0
    while n < len(demo.pages):
        $ page = demo.pages[n]
        show text "[page]"
        pause
        $ n += 1

    hide text
    $ renpy.utter_restart()
