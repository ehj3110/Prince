import pyglet

# Open on the secondary display (the DLP)
display = pyglet.display.get_display()
screens = display.get_screens()
target_screen = screens[1] if len(screens) > 1 else screens[0]

window = pyglet.window.Window(fullscreen=True, screen=target_screen)

@window.event
def on_draw():
    window.clear()
    pyglet.gl.glClearColor(1.0, 1.0, 1.0, 1.0) # Pure White
    pyglet.gl.glClear(pyglet.gl.GL_COLOR_BUFFER_BIT)

print("Projecting pure white monitor signal. Press ESC to close.")
pyglet.app.run()