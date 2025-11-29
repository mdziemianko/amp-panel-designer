import svgwrite
from models import Panel, Group, Potentiometer, Socket, Switch, Element, FontStyle

class PanelRenderer:
    def __init__(self, panel: Panel):
        self.panel = panel
        self.dwg = svgwrite.Drawing(size=(f"{panel.width}mm", f"{panel.height}mm"), viewBox=f"0 0 {panel.width} {panel.height}")
        # Set background
        self.dwg.add(self.dwg.rect(insert=(0, 0), size=(panel.width, panel.height), fill=panel.background_color))

    def render(self, filename: str):
        self._render_group(self.panel.elements, 0, 0)
        self.dwg.saveas(filename)

    def _get_text_width(self, text: str, font_size: float) -> float:
        # Simple estimation: average character width approx 0.6 * font_size
        # font_size is expected to be in mm (user units)
        # If it somehow comes in as a string (e.g. from default or unparsed), try to parse float
        if isinstance(font_size, str):
            try:
                # Naive strip if units persist
                val = font_size.lower().replace("pt", "").replace("px", "").replace("mm", "")
                font_size = float(val)
            except ValueError:
                font_size = 3.0 # fallback approx 10-12pt
        return len(text) * font_size * 0.6

    def _render_group(self, elements: list[Element], offset_x: float, offset_y: float):
        for element in elements:
            abs_x = offset_x + element.x
            abs_y = offset_y + element.y
            
            if isinstance(element, Group):
                label_gap = None
                
                # Render group label if exists
                if element.label:
                    label_x = abs_x
                    if element.width:
                         label_x += element.width / 2
                    
                    # Use group's font style or default for groups
                    font_style = element.font_style
                    default_size = 4.0 # approx 11-12pt in mm
                    size = font_style.size if font_style and font_style.size else default_size
                    
                    # Ensure size is a float for calculations
                    try:
                        if isinstance(size, str):
                             val = size.lower().replace("pt", "").replace("px", "").replace("mm", "")
                             size_val = float(val)
                        else:
                             size_val = float(size)
                    except ValueError:
                        size_val = 4.0

                    pos = element.label_position if element.label_position else 'top'
                    label_y = abs_y
                    
                    text_width = self._get_text_width(element.label, size_val)
                    
                    if pos == 'top':
                        label_y = abs_y - 5
                    elif pos == 'top_inline':
                        label_y = abs_y + size_val * 0.35 # Vertical center on line
                        label_gap = (label_x - text_width/2 - 2, label_x + text_width/2 + 2) # Add some padding
                    elif pos == 'top_internal':
                         label_y = abs_y + size_val + 2
                    elif pos == 'bottom':
                        label_y = abs_y + (element.height if element.height else 0) + size_val + 2
                    elif pos == 'bottom_inline':
                         label_y = abs_y + (element.height if element.height else 0) + size_val * 0.35
                         label_gap = (label_x - text_width/2 - 2, label_x + text_width/2 + 2)
                    elif pos == 'bottom_internal':
                         label_y = abs_y + (element.height if element.height else 0) - 5

                    self._render_text(element.label, label_x, label_y, default_size=default_size, default_weight='bold', font_style=font_style)

                # Render border with potential gap
                self._render_border(element, abs_x, abs_y, label_gap=label_gap, label_pos=element.label_position)
                
                # Render children
                self._render_group(element.elements, abs_x, abs_y)
            
            elif isinstance(element, Potentiometer):
                self._render_potentiometer(element, abs_x, abs_y)
            
            elif isinstance(element, Socket):
                self._render_socket(element, abs_x, abs_y)
            
            elif isinstance(element, Switch):
                self._render_switch(element, abs_x, abs_y)

    def _render_border(self, group: Group, x: float, y: float, label_gap=None, label_pos=None):
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

        # Helper for gap line
        def draw_line_with_gap(x1, y1, x2, y2, gap):
            if not gap:
                draw_line(x1, y1, x2, y2)
                return
            
            gap_start, gap_end = gap
            # Draw left part
            if gap_start > x1:
                 draw_line(x1, y1, gap_start, y1)
            # Draw right part
            if gap_end < x2:
                 draw_line(gap_end, y1, x2, y1)

        if b.type == 'full':
            # Draw manually to support gaps
            # Top
            if label_pos == 'top_inline':
                draw_line_with_gap(x, y, x + group.width, y, label_gap)
            else:
                draw_line(x, y, x + group.width, y)
                
            # Bottom
            if label_pos == 'bottom_inline':
                draw_line_with_gap(x, y + group.height, x + group.width, y + group.height, label_gap)
            else:
                draw_line(x, y + group.height, x + group.width, y + group.height)
                
            # Left
            draw_line(x, y, x, y + group.height)
            # Right
            draw_line(x + group.width, y, x + group.width, y + group.height)
            
        elif b.type == 'top':
             if label_pos == 'top_inline':
                 draw_line_with_gap(x, y, x + group.width, y, label_gap)
             else:
                draw_line(x, y, x + group.width, y)
        elif b.type == 'bottom':
             if label_pos == 'bottom_inline':
                 draw_line_with_gap(x, y + group.height, x + group.width, y + group.height, label_gap)
             else:
                draw_line(x, y + group.height, x + group.width, y + group.height)

    def _render_potentiometer(self, pot: Potentiometer, x: float, y: float):
        # Circle
        self.dwg.add(self.dwg.circle(center=(x, y), r=pot.radius, fill='none', stroke='black', stroke_width=1))
        # Knob marker (pointing up for now)
        self.dwg.add(self.dwg.line(start=(x, y), end=(x, y - pot.radius + 2), stroke='black', stroke_width=2))
        
        # Label
        if pot.label:
            pos = pot.label_position if pot.label_position else 'bottom'
            if pos == 'top':
                 label_y = y - pot.radius - 5
            else:
                 label_y = y + pot.radius + 15
            
            self._render_text(pot.label, x, label_y, font_style=pot.font_style)
        
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
            pos = socket.label_position if socket.label_position else 'bottom'
            if pos == 'top':
                 label_y = y - socket.radius - 5
            else:
                 label_y = y + socket.radius + 15
            self._render_text(socket.label, x, label_y, font_style=socket.font_style)

    def _render_switch(self, switch: Switch, x: float, y: float):
        # Rect
        self.dwg.add(self.dwg.rect(insert=(x - switch.width/2, y - switch.height/2), 
                                   size=(switch.width, switch.height), 
                                   fill='#cccccc', stroke='black'))
        # Lever
        self.dwg.add(self.dwg.circle(center=(x, y), r=switch.width/2 - 2, fill='black'))
        
        if switch.label:
            pos = switch.label_position if switch.label_position else 'bottom'
            if pos == 'top':
                 label_y = y - switch.height/2 - 5
            else:
                 label_y = y + switch.height/2 + 15
            self._render_text(switch.label, x, label_y, font_style=switch.font_style)

    def _render_text(self, text: str, x: float, y: float, default_size=12, default_weight='normal', font_style: FontStyle = None):
        size = default_size
        weight = default_weight
        color = 'black'
        family = 'sans-serif'
        
        if font_style:
            if font_style.size:
                size = font_style.size
            if font_style.weight:
                weight = font_style.weight
            if font_style.color:
                color = font_style.color
            if font_style.family:
                family = font_style.family

        self.dwg.add(self.dwg.text(text, insert=(x, y), 
                                   text_anchor="middle", 
                                   font_family=family, 
                                   font_size=size,
                                   font_weight=weight,
                                   fill=color))
