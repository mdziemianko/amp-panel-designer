import svgwrite
from models import Panel, Group, Potentiometer, Socket, Switch, Element

class PanelRenderer:
    def __init__(self, panel: Panel):
        self.panel = panel
        self.dwg = svgwrite.Drawing(size=(f"{panel.width}mm", f"{panel.height}mm"), viewBox=f"0 0 {panel.width} {panel.height}")
        # Set background
        self.dwg.add(self.dwg.rect(insert=(0, 0), size=(panel.width, panel.height), fill=panel.background_color))

    def render(self, filename: str):
        self._render_group(self.panel.elements, 0, 0)
        self.dwg.saveas(filename)

    def _render_group(self, elements: list[Element], offset_x: float, offset_y: float):
        for element in elements:
            abs_x = offset_x + element.x
            abs_y = offset_y + element.y
            
            if isinstance(element, Group):
                # Render border
                self._render_border(element, abs_x, abs_y)

                # Render group label if exists
                if element.label:
                    label_x = abs_x
                    if element.width:
                         label_x += element.width / 2
                    self._render_text(element.label, label_x, abs_y - 5, font_size=14, font_weight='bold') # Slightly above group origin
                
                # Render children
                self._render_group(element.elements, abs_x, abs_y)
            
            elif isinstance(element, Potentiometer):
                self._render_potentiometer(element, abs_x, abs_y)
            
            elif isinstance(element, Socket):
                self._render_socket(element, abs_x, abs_y)
            
            elif isinstance(element, Switch):
                self._render_switch(element, abs_x, abs_y)

    def _render_border(self, group: Group, x: float, y: float):
        if not group.border or group.border.type == 'none':
            return
            
        if not group.width or not group.height:
             # Can't draw border without dimensions
            return

        b = group.border
        stroke_dasharray = None
        if b.style == 'dotted':
            stroke_dasharray = "2,2"
        elif b.style == 'dashed':
             stroke_dasharray = "5,5"
        
        # Helper to draw line
        def draw_line(x1, y1, x2, y2):
             kwargs = {
                 'stroke': b.color,
                 'stroke_width': b.thickness
             }
             if stroke_dasharray:
                 kwargs['stroke_dasharray'] = stroke_dasharray
             self.dwg.add(self.dwg.line(start=(x1, y1), end=(x2, y2), **kwargs))

        if b.type == 'full':
            kwargs = {
                 'fill': 'none',
                 'stroke': b.color,
                 'stroke_width': b.thickness
            }
            if stroke_dasharray:
                 kwargs['stroke_dasharray'] = stroke_dasharray
            self.dwg.add(self.dwg.rect(insert=(x, y), size=(group.width, group.height), **kwargs))
        elif b.type == 'top':
            draw_line(x, y, x + group.width, y)
        elif b.type == 'bottom':
            draw_line(x, y + group.height, x + group.width, y + group.height)

    def _render_potentiometer(self, pot: Potentiometer, x: float, y: float):
        # Circle
        self.dwg.add(self.dwg.circle(center=(x, y), r=pot.radius, fill='none', stroke='black', stroke_width=1))
        # Knob marker (pointing up for now)
        self.dwg.add(self.dwg.line(start=(x, y), end=(x, y - pot.radius + 2), stroke='black', stroke_width=2))
        
        # Label
        if pot.label:
            self._render_text(pot.label, x, y + pot.radius + 15) # Below
        
        # Scale (simplified)
        if pot.scale:
             # Just drawing a few ticks for representation
            for i in range(-135, 136, 27): # -135 to +135 degrees
                # Need math for coords, skipping for simplicity of first pass or adding basic math
                pass

    def _render_socket(self, socket: Socket, x: float, y: float):
        # Outer circle
        self.dwg.add(self.dwg.circle(center=(x, y), r=socket.radius, fill='#333333', stroke='black', stroke_width=1))
        # Inner hole
        self.dwg.add(self.dwg.circle(center=(x, y), r=socket.radius/2, fill='black'))
        
        if socket.label:
            self._render_text(socket.label, x, y + socket.radius + 15)

    def _render_switch(self, switch: Switch, x: float, y: float):
        # Rect
        self.dwg.add(self.dwg.rect(insert=(x - switch.width/2, y - switch.height/2), 
                                   size=(switch.width, switch.height), 
                                   fill='#cccccc', stroke='black'))
        # Lever
        self.dwg.add(self.dwg.circle(center=(x, y), r=switch.width/2 - 2, fill='black'))
        
        if switch.label:
            self._render_text(switch.label, x, y + switch.height/2 + 15)

    def _render_text(self, text: str, x: float, y: float, font_size=12, font_weight='normal'):
        self.dwg.add(self.dwg.text(text, insert=(x, y), 
                                   text_anchor="middle", 
                                   font_family="sans-serif", 
                                   font_size=font_size,
                                   font_weight=font_weight,
                                   fill='black'))
