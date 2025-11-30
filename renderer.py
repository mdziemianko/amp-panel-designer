import svgwrite
import math
from typing import Optional
from models import Panel, Group, Potentiometer, Socket, Switch, Element, FontStyle, Component

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
        if isinstance(font_size, str):
            try:
                val = font_size.lower().replace("pt", "").replace("px", "").replace("mm", "")
                font_size = float(val)
            except ValueError:
                font_size = 3.0 # fallback
        return len(text) * font_size * 0.6

    def _render_drill_pattern(self, x: float, y: float, mount: Optional[Component] = None, diameter=None, shape='circular', width=None, height=None):
        # Allow passing Mount object or legacy args for compatibility/simplicity
        # If mount object is passed, extract values
        
        m_diameter = diameter
        m_width = width
        m_height = height
        m_shape = shape
        
        if hasattr(mount, 'mount') and mount.mount:
             # It's a component with a mount object
             if mount.mount.diameter:
                  m_diameter = mount.mount.diameter
                  m_shape = 'circular'
             elif mount.mount.width and mount.mount.height:
                  m_width = mount.mount.width
                  m_height = mount.mount.height
                  m_shape = 'rectangular'
        
        if m_shape == 'rectangular' and m_width and m_height:
            # Rectangular hole
            self.dwg.add(self.dwg.rect(insert=(x - m_width/2, y - m_height/2), 
                                       size=(m_width, m_height), 
                                       fill='none', stroke='gray', stroke_width=0.5, stroke_opacity=0.5))
            # Cross center
            cross_len_h = m_width/2 + 3.0
            cross_len_v = m_height/2 + 3.0
            self.dwg.add(self.dwg.line(start=(x - cross_len_h, y), end=(x + cross_len_h, y), 
                                       stroke='gray', stroke_width=0.5, stroke_opacity=0.5))
            self.dwg.add(self.dwg.line(start=(x, y - cross_len_v), end=(x, y + cross_len_v), 
                                       stroke='gray', stroke_width=0.5, stroke_opacity=0.5))
        elif m_diameter:
            # Circular hole
            r = m_diameter / 2
            self.dwg.add(self.dwg.circle(center=(x, y), r=r, fill='none', stroke='gray', stroke_width=0.5, stroke_opacity=0.5))
            cross_len = r + 3.0
            self.dwg.add(self.dwg.line(start=(x - cross_len, y), end=(x + cross_len, y), stroke='gray', stroke_width=0.5, stroke_opacity=0.5))
            self.dwg.add(self.dwg.line(start=(x, y - cross_len), end=(x, y + cross_len), stroke='gray', stroke_width=0.5, stroke_opacity=0.5))


    def _should_show_component(self):
        return self.panel.render_mode in ('show', 'both')

    def _should_show_drill(self):
        return self.panel.render_mode in ('hide', 'both')
        
    def _is_both_mode(self):
        return self.panel.render_mode == 'both'

    def _get_element_font(self, element: Element) -> Optional[FontStyle]:
        # Priority: element.label.font -> element.font_style -> None
        if element.label and element.label.font:
            return element.label.font
        return element.font_style

    def _render_group(self, elements: list[Element], offset_x: float, offset_y: float):
        for element in elements:
            abs_x = offset_x + element.x
            abs_y = offset_y + element.y
            
            if isinstance(element, Group):
                label_gap = None
                
                # Render group label if exists
                if element.label and element.label.text:
                    label_text = element.label.text
                    label_x = abs_x
                    if element.width:
                         label_x += element.width / 2
                    
                    font_style = self._get_element_font(element)
                    
                    default_size = 4.0
                    size = font_style.size if font_style and font_style.size else default_size
                    
                    try:
                        if isinstance(size, str):
                             val = size.lower().replace("pt", "").replace("px", "").replace("mm", "")
                             size_val = float(val)
                        else:
                             size_val = float(size)
                    except ValueError:
                        size_val = 4.0

                    pos = element.label.position if element.label.position else 'top-outside'
                    label_y = abs_y
                    
                    text_width = self._get_text_width(label_text, size_val)
                    
                    if pos == 'top-outside':
                        label_y = abs_y - 5
                    elif pos == 'top-inline':
                        label_y = abs_y + size_val * 0.35 
                        label_gap = (label_x - text_width/2 - 2, label_x + text_width/2 + 2)
                    elif pos == 'top-inside':
                         label_y = abs_y + size_val + 2
                    elif pos == 'bottom-outside':
                        label_y = abs_y + (element.height if element.height else 0) + size_val + 2
                    elif pos == 'bottom-inline':
                         label_y = abs_y + (element.height if element.height else 0) + size_val * 0.35
                         label_gap = (label_x - text_width/2 - 2, label_x + text_width/2 + 2)
                    elif pos == 'bottom-inside':
                         label_y = abs_y + (element.height if element.height else 0) - 5

                    self._render_text(label_text, label_x, label_y, default_size=default_size, default_weight='bold', font_style=font_style)

                self._render_border(element, abs_x, abs_y, label_gap=label_gap, label_pos=element.label.position if element.label else None)
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
            return

        b = group.border
        stroke_dasharray = None
        if b.style == 'dotted':
            stroke_dasharray = "2,2"
        elif b.style == 'dashed':
             stroke_dasharray = "5,5"
        
        def draw_line(x1, y1, x2, y2):
             kwargs = {
                 'stroke': b.color,
                 'stroke_width': b.thickness
             }
             if stroke_dasharray:
                 kwargs['stroke_dasharray'] = stroke_dasharray
             self.dwg.add(self.dwg.line(start=(x1, y1), end=(x2, y2), **kwargs))

        def draw_line_with_gap(x1, y1, x2, y2, gap):
            if not gap:
                draw_line(x1, y1, x2, y2)
                return
            
            gap_start, gap_end = gap
            if gap_start > x1:
                 draw_line(x1, y1, gap_start, y1)
            if gap_end < x2:
                 draw_line(gap_end, y1, x2, y1)

        if b.type == 'full':
            if label_pos == 'top-inline':
                draw_line_with_gap(x, y, x + group.width, y, label_gap)
            else:
                draw_line(x, y, x + group.width, y)
                
            if label_pos == 'bottom-inline':
                draw_line_with_gap(x, y + group.height, x + group.width, y + group.height, label_gap)
            else:
                draw_line(x, y + group.height, x + group.width, y + group.height)
                
            draw_line(x, y, x, y + group.height)
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
        knob_radius = pot.knob_diameter / 2
        component_opacity = 0.5 if self._is_both_mode() else 1.0
        
        if self._should_show_drill():
            self._render_drill_pattern(x, y, mount=pot)

        if pot.border_thickness > 0:
            border_r = pot.border_diameter / 2
            self.dwg.add(self.dwg.circle(center=(x, y), r=border_r, 
                                         fill='none', stroke='black', stroke_width=pot.border_thickness))

        if pot.scale:
             s = pot.scale
             start_angle_user = pot.angle_start
             sweep_angle_user = pot.angle_width
             
             if s.num_ticks > 0:
                step = sweep_angle_user / (s.num_ticks - 1) if s.num_ticks > 1 else 0
                
                base_radius = (pot.border_diameter / 2) if pot.border_diameter > pot.knob_diameter else (pot.knob_diameter / 2)
                tick_r_start = base_radius + 1.0 
                
                for i in range(s.num_ticks):
                    angle_user = start_angle_user + i * step
                    angle_svg_deg = angle_user + 90
                    angle_rad = math.radians(angle_svg_deg)
                    
                    is_major = (i % s.major_tick_interval == 0) if s.major_tick_interval > 0 else True
                    
                    current_tick_len = s.tick_size if is_major else s.tick_size * 0.5
                    
                    x1 = x + tick_r_start * math.cos(angle_rad)
                    y1 = y + tick_r_start * math.sin(angle_rad)
                    
                    if s.tick_style == 'dot':
                        r_dot = (current_tick_len / 2) if is_major else (current_tick_len / 4)
                        x_dot = x + (tick_r_start + r_dot) * math.cos(angle_rad)
                        y_dot = y + (tick_r_start + r_dot) * math.sin(angle_rad)
                        
                        self.dwg.add(self.dwg.circle(center=(x_dot, y_dot), r=r_dot, fill='black'))
                    else: # line
                        x2 = x + (tick_r_start + current_tick_len) * math.cos(angle_rad)
                        y2 = y + (tick_r_start + current_tick_len) * math.sin(angle_rad)
                        self.dwg.add(self.dwg.line(start=(x1, y1), end=(x2, y2), stroke='black', stroke_width=1 if not is_major else 1.5))

        if self._should_show_component():
            self.dwg.add(self.dwg.circle(center=(x, y), r=knob_radius, fill='white', stroke='black', stroke_width=1, opacity=component_opacity))
            self.dwg.add(self.dwg.line(start=(x, y), end=(x, y - knob_radius + 2), stroke='black', stroke_width=2, opacity=component_opacity))
            
        # Label
        if pot.label and pot.label.text:
            pos = pot.label.position if pot.label.position else 'bottom'
            
            outer_radius = (pot.border_diameter / 2)
            if pot.scale:
                outer_radius += pot.scale.tick_size + 2
                
            dist = max(outer_radius, pot.knob_diameter/2) + 2 
            
            if pos == 'top':
                 label_y = y - dist - 4 
            else:
                 label_y = y + dist + 4 + 2
            
            font_style = self._get_element_font(pot)
            self._render_text(pot.label.text, x, label_y, font_style=font_style)

    def _render_socket(self, socket: Socket, x: float, y: float):
        component_opacity = 0.5 if self._is_both_mode() else 1.0
        
        if self._should_show_drill():
             self._render_drill_pattern(x, y, mount=socket)

        if self._should_show_component():
            self.dwg.add(self.dwg.circle(center=(x, y), r=socket.radius, fill='#333333', stroke='black', stroke_width=1, opacity=component_opacity))
            self.dwg.add(self.dwg.circle(center=(x, y), r=socket.radius/2, fill='black', opacity=component_opacity))
        
        if socket.label and socket.label.text:
            pos = socket.label.position if socket.label.position else 'bottom'
            if pos == 'top':
                 label_y = y - socket.radius - 5
            else:
                 label_y = y + socket.radius + 15
            font_style = self._get_element_font(socket)
            self._render_text(socket.label.text, x, label_y, font_style=font_style)

    def _render_switch(self, switch: Switch, x: float, y: float):
        component_opacity = 0.5 if self._is_both_mode() else 1.0
        
        # Drill pattern
        if self._should_show_drill():
             self._render_drill_pattern(x, y, mount=switch)

        # Switch Labels (Top/Center/Bottom)
        if switch.switch_type == 'toggle':
            # Render labels always (printed)
            font_style = self._get_element_font(switch)
            if switch.label_top:
                self._render_text(switch.label_top, x, y - switch.height/2 - 5, font_style=font_style)
            if switch.label_bottom:
                self._render_text(switch.label_bottom, x, y + switch.height/2 + 8, font_style=font_style)
            if switch.label_center:
                # To the right?
                self._render_text(switch.label_center, x + switch.width/2 + 8, y + 2, font_style=font_style)

        # Rotary Switch Scale and Labels
        if switch.switch_type == 'rotary':
             # Reuse potentiometer logic partially or fully?
             # It needs to render labels at ticks
             if switch.scale:
                 s = switch.scale
                 start_angle_user = switch.angle_start
                 sweep_angle_user = switch.angle_width
                 
                 step = sweep_angle_user / (s.num_ticks - 1) if s.num_ticks > 1 else 0
                 
                 # Base radius for ticks
                 # Rotary usually has knob_diameter
                 base_radius = switch.knob_diameter / 2
                 tick_r_start = base_radius + 1.0
                 
                 for i in range(s.num_ticks):
                    angle_user = start_angle_user + i * step
                    angle_svg_deg = angle_user + 90
                    angle_rad = math.radians(angle_svg_deg)
                    
                    is_major = (i % s.major_tick_interval == 0) if s.major_tick_interval > 0 else True
                    
                    current_tick_len = s.tick_size if is_major else s.tick_size * 0.5
                    
                    x1 = x + tick_r_start * math.cos(angle_rad)
                    y1 = y + tick_r_start * math.sin(angle_rad)
                    
                    # Draw tick
                    if s.tick_style == 'dot':
                        r_dot = (current_tick_len / 2) if is_major else (current_tick_len / 4)
                        x_dot = x + (tick_r_start + r_dot) * math.cos(angle_rad)
                        y_dot = y + (tick_r_start + r_dot) * math.sin(angle_rad)
                        self.dwg.add(self.dwg.circle(center=(x_dot, y_dot), r=r_dot, fill='black'))
                        label_anchor_radius = tick_r_start + r_dot * 2 + 2 # push out
                    else: # line
                        x2 = x + (tick_r_start + current_tick_len) * math.cos(angle_rad)
                        y2 = y + (tick_r_start + current_tick_len) * math.sin(angle_rad)
                        self.dwg.add(self.dwg.line(start=(x1, y1), end=(x2, y2), stroke='black', stroke_width=1 if not is_major else 1.5))
                        label_anchor_radius = tick_r_start + current_tick_len + 3 # push out
                    
                    # Draw label if exists
                    if i < len(switch.scale_labels):
                        label_text = switch.scale_labels[i]
                        lx = x + label_anchor_radius * math.cos(angle_rad)
                        ly = y + label_anchor_radius * math.sin(angle_rad)
                        # Adjust ly slightly for vertical centering? _render_text does some of that
                        font_style = self._get_element_font(switch)
                        self._render_text(label_text, lx, ly + 1.5, default_size=3.0, font_style=font_style)

        if self._should_show_component():
            if switch.switch_type == 'rotary':
                # Similar to potentiometer knob
                knob_radius = switch.knob_diameter / 2
                self.dwg.add(self.dwg.circle(center=(x, y), r=knob_radius, fill='white', stroke='black', stroke_width=1, opacity=component_opacity))
                # Marker
                self.dwg.add(self.dwg.line(start=(x, y), end=(x, y - knob_radius + 2), stroke='black', stroke_width=2, opacity=component_opacity))
            else: # toggle
                self.dwg.add(self.dwg.rect(insert=(x - switch.width/2, y - switch.height/2), 
                                           size=(switch.width, switch.height), 
                                           fill='#cccccc', stroke='black', opacity=component_opacity))
                self.dwg.add(self.dwg.circle(center=(x, y), r=switch.width/2 - 2, fill='black', opacity=component_opacity))
        
        # Main Label
        if switch.label and switch.label.text:
            pos = switch.label.position if switch.label.position else 'bottom'
            
            # Distance logic for toggle vs rotary
            if switch.switch_type == 'rotary':
                 # calculate max radius used by scale/labels
                 # Simplify: knob/2 + tick size + padding + label space
                 dist = switch.knob_diameter/2 + 5 
                 if switch.scale:
                     dist += switch.scale.tick_size + 5
            else:
                 dist = switch.height/2 + 10 # toggle height based
            
            if pos == 'top':
                 label_y = y - dist - 5
            else:
                 label_y = y + dist + 5
            
            font_style = self._get_element_font(switch)
            self._render_text(switch.label.text, x, label_y, font_style=font_style)

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
