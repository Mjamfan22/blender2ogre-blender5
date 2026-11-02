"""Capture the isolated preview through Blender's own screenshot operator."""
from pathlib import Path
import json
import bpy

ROOT = Path(__file__).resolve().parents[1]
def capture():
    window = bpy.context.window_manager.windows[0]
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            space.shading.type = 'SOLID'
            space.shading.color_type = 'MATERIAL'
            space.overlay.show_extras = False
            space.overlay.show_axis_x = False
            space.overlay.show_axis_y = False
            region = next(item for item in area.regions if item.type == 'WINDOW')
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=2)
    output = ROOT / 'docs/images/blender-viewport.png'
    with bpy.context.temp_override(window=window):
        bpy.ops.screen.screenshot(filepath=str(output))
    (ROOT / '.build/outputs/viewport_capture.json').write_text(json.dumps({
        'method': 'bpy.ops.screen.screenshot', 'blender': bpy.app.version_string,
        'areas': [area.type for area in window.screen.areas], 'output': output.name,
    }, indent=2))
    def close_preview():
        bpy.ops.wm.quit_blender()
        return None
    bpy.app.timers.register(close_preview, first_interval=2)
    return None
bpy.app.timers.register(capture, first_interval=5)
