import svgwrite
import math
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

                    pos = element.label_position if element.label_position else 'top-outside'
                    label_y = abs_y
                    
                    text_width = self._get_text_width(element.label, size_val)
                    
                    if pos == 'top-outside':
                        label_y = abs_y - 5
                    elif pos == 'top-inline':
                        label_y = abs_y + size_val * 0.35 # Vertical center on line
                        label_gap = (label_x - text_width/2 - 2, label_x + text_width/2 + 2) # Add some padding
                    elif pos == 'top-inside':
                         label_y = abs_y + size_val + 2
                    elif pos == 'bottom-outside':
                        label_y = abs_y + (element.height if element.height else 0) + size_val + 2
                    elif pos == 'bottom-inline':
                         label_y = abs_y + (element.height if element.height else 0) + size_val * 0.35
                         label_gap = (label_x - text_width/2 - 2, label_x + text_width/2 + 2)
                    elif pos == 'bottom-inside':
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
            if label_pos == 'top-inline':
                draw_line_with_gap(x, y, x + group.width, y, label_gap)
            else:
                draw_line(x, y, x + group.width, y)
                
            # Bottom
            if label_pos == 'bottom-inline':
                draw_line_with_gap(x, y + group.height, x + group.width, y + group.height, label_gap)
            else:
                draw_line(x, y + group.height, x + group.width, y + group.height)
                
            # Left
            draw_line(x, y, x, y + group.height)
            # Right
            draw_line(x + group.width, y, x + group.width, y + group.height)
            
        elif b.type == 'top':
             if label_pos == 'top-inline':
                 draw_line_with_gap(x, y, x + group.width, y, label_gap)
             else:
                draw_line(x, y, x + group.width, y)
        elif b.type == 'bottom':
             if label_pos == 'bottom-inline':
                 draw_line_with_gap(x, y + group.height, x + group.width, y + group.height, label_gap)
             else:
                draw_line(x, y + group.height, x + group.width, y + group.height)

    def _render_potentiometer(self, pot: Potentiometer, x: float, y: float):
        # Constants and defaults
        knob_radius = pot.knob_diameter / 2
        
        # Border (Circular)
        if pot.border_thickness > 0:
            border_r = pot.border_diameter / 2
            # For a circle border (full 360)
            self.dwg.add(self.dwg.circle(center=(x, y), r=border_r, 
                                         fill='none', stroke='black', stroke_width=pot.border_thickness))

        # Scale
        if pot.scale:
             s = pot.scale
             
             # Calculate angles
             # User: 0 is down (6 o'clock), clockwise.
             # SVG: 0 is right (3 o'clock), clockwise.
             # Transform: SVG = User + 90
             
             start_angle_user = pot.angle_start
             sweep_angle_user = pot.angle_width
             
             # Draw ticks
             if s.num_ticks > 0:
                step = sweep_angle_user / (s.num_ticks - 1) if s.num_ticks > 1 else 0
                
                # Scale radius: relative to what? usually outside the knob or border
                # If position is 'outside', maybe based on border_diameter or knob_diameter?
                # User said "scale position with respect ot border".
                # Let's assume default radius is slightly larger than border radius if border exists, or knob radius.
                # Default logic: radius = border_diameter/2 + tick_size/2 + padding?
                # Or maybe s.radius if provided?
                # Let's define base radius:
                base_radius = (pot.border_diameter / 2) if pot.border_diameter > pot.knob_diameter else (pot.knob_diameter / 2)
                # Apply position modifier? Just use base_radius + 2mm padding for now or if position logic is strictly needed.
                # Simplification: ticks start at base_radius + 2
                
                tick_r_start = base_radius + 1.0 # gap from component
                
                for i in range(s.num_ticks):
                    angle_user = start_angle_user + i * step
                    angle_svg_deg = angle_user + 90
                    angle_rad = math.radians(angle_svg_deg)
                    
                    is_major = (i % s.major_tick_interval == 0) if s.major_tick_interval > 0 else True
                    
                    current_tick_len = s.tick_size if is_major else s.tick_size * 0.5
                    
                    # Coords
                    # x = cx + r * cos(a)
                    # y = cy + r * sin(a)
                    
                    x1 = x + tick_r_start * math.cos(angle_rad)
                    y1 = y + tick_r_start * math.sin(angle_rad)
                    
                    if s.tick_style == 'dot':
                        r_dot = (current_tick_len / 2) if is_major else (current_tick_len / 4) # rough scaling
                        # For dot, (x1, y1) is center? No, let's push it out by radius so it sits outside
                        x_dot = x + (tick_r_start + r_dot) * math.cos(angle_rad)
                        y_dot = y + (tick_r_start + r_dot) * math.sin(angle_rad)
                        
                        self.dwg.add(self.dwg.circle(center=(x_dot, y_dot), r=r_dot, fill='black'))
                    else: # line
                        x2 = x + (tick_r_start + current_tick_len) * math.cos(angle_rad)
                        y2 = y + (tick_r_start + current_tick_len) * math.sin(angle_rad)
                        self.dwg.add(self.dwg.line(start=(x1, y1), end=(x2, y2), stroke='black', stroke_width=1 if not is_major else 1.5))

        # Knob (drawn on top)
        self.dwg.add(self.dwg.circle(center=(x, y), r=knob_radius, fill='white', stroke='black', stroke_width=1))
        # Knob marker (pointing to current value? defaults to center/up?)
        # Let's point it to center of travel? Or just up? User said 0 degrees is straight down.
        # Let's point it up (180 deg user => 270 deg svg).
        # Or let's just keep the simple line up for now.
        self.dwg.add(self.dwg.line(start=(x, y), end=(x, y - knob_radius + 2), stroke='black', stroke_width=2))
        
        # Label
        if pot.label:
            pos = pot.label_position if pot.label_position else 'bottom'
            
            # Distance from center depends on knob, border, and scale
            # Max radius involved
            outer_radius = (pot.border_diameter / 2)
            if pot.scale:
                # Add tick length + padding
                outer_radius += pot.scale.tick_size + 2
                
            dist = max(outer_radius, pot.knob_diameter/2) + 2 # + padding
            
            if pos == 'top':
                 label_y = y - dist - 4 # font height approx
            else:
                 label_y = y + dist + 4 + 2
            
            self._render_text(pot.label, x, label_y, font_style=pot.font_style)

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
