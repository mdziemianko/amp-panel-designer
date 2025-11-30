import svgwrite
import math
from typing import Optional
from models import Panel, Group, Potentiometer, Socket, Switch, Element, FontStyle, Component, Custom

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

    def _get_font_size_mm(self, font_style: Optional[FontStyle], default_mm=3.0) -> float:
        if not font_style or not font_style.size:
            return default_mm
        
        size = font_style.size
        if isinstance(size, (int, float)):
            return float(size)
        
        # Parse string
        if isinstance(size, str):
            val = size.strip().lower()
            try:
                if val.endswith('mm'):
                    return float(val[:-2])
                elif val.endswith('pt'):
                    return float(val[:-2]) * (25.4 / 72.0)
                elif val.endswith('px'):
                    return float(val[:-2]) * (25.4 / 96.0)
                else:
                    return float(val) # assume mm if no unit? or pt? default assumption elsewhere is mm
            except ValueError:
                pass
        return default_mm

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

            elif isinstance(element, Custom):
                self._render_custom(element, abs_x, abs_y)

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
            font_style = self._get_element_font(pot)
            font_size = self._get_font_size_mm(font_style)
            
            # Default distance calculation
            outer_radius = (pot.border_diameter / 2)
            if pot.scale:
                outer_radius += pot.scale.tick_size + 2
            dist = max(outer_radius, pot.knob_diameter/2) + 2 
            
            # Override with explicit distance if provided
            if pot.label.distance is not None:
                dist = pot.label.distance
            
            # Calculate position
            # If bottom: Top of label at dist. Baseline = y + dist + font_size*0.7
            # If top: Bottom of label at dist. Baseline = y - dist
            if pos == 'top':
                 label_y = y - dist
            else:
                 label_y = y + dist + font_size * 0.7
            
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
            font_style = self._get_element_font(socket)
            font_size = self._get_font_size_mm(font_style)
            
            dist = socket.radius + 5
            if socket.label.distance is not None:
                dist = socket.label.distance
                
            if pos == 'top':
                 label_y = y - dist
            else:
                 label_y = y + dist + font_size * 0.7
                 
            self._render_text(socket.label.text, x, label_y, font_style=font_style)

    def _render_switch(self, switch: Switch, x: float, y: float):
        component_opacity = 0.5 if self._is_both_mode() else 1.0
        
        # Drill pattern
        if self._should_show_drill():
             self._render_drill_pattern(x, y, mount=switch)

        # Switch Labels (Top/Center/Bottom)
        if switch.switch_type == 'toggle':
            # Render labels always (printed)
            default_font_style = self._get_element_font(switch)
            
            # Helper for toggle label pos
            def render_toggle_label(lbl_obj, default_text, default_pos_offset):
                # default_pos_offset is tuple (dx, dy) from center (x,y)
                # If explicit distance is provided, it replaces the default offset magnitude?
                # Toggle logic is tricky because 'top'/'bottom' are positions, not just distance.
                # Let's keep existing logic but apply font shift if top/bottom
                
                # However, toggle labels (label_top, label_bottom) are separate from main label.
                # They don't have 'distance' property in Label object usually?
                # Wait, I added distance to Label. So yes they might.
                
                font = lbl_obj.font if lbl_obj and lbl_obj.font else default_font_style
                text = lbl_obj.text if lbl_obj else default_text
                if not text: return
                
                f_size = self._get_font_size_mm(font)
                
                # Base offset
                dx, dy = default_pos_offset
                
                # Adjust dy for top/bottom based on distance logic?
                # If lbl_obj.distance is set, use it.
                # If top label (dy < 0): distance is from center to bottom of label?
                #   y_target = y - distance.
                # If bottom label (dy > 0): distance is from center to top of label?
                #   y_target = y + distance + font_size * 0.7
                
                # We need to know if it's top or bottom label.
                # Assume based on dy sign.
                
                final_x = x + dx
                final_y = y + dy
                
                if lbl_obj and lbl_obj.distance is not None:
                    d = lbl_obj.distance
                    if dy < 0: # top
                        final_y = y - d
                    elif dy > 0: # bottom
                        final_y = y + d + f_size * 0.7
                    # Center label (dy=0)? Distance usually x-offset? 
                    # Let's ignore distance for center label horizontal shift for now unless requested.
                else:
                    # Apply baseline correction to default positions too?
                    # Default Top: y - height/2 - 5. This is baseline.
                    # Text is above baseline. So bottom of text is at y - height/2 - 5.
                    # This matches "Bottom of label if above". OK.
                    
                    # Default Bottom: y + height/2 + 8. This is baseline.
                    # Text is above baseline.
                    # Top of text is at y + height/2 + 8 - font_size*0.7.
                    # User wants standard behavior to be "distance is to top of label".
                    # Here "8" is the padding. 
                    # If I want padding 5mm, I should set baseline to y + height/2 + 5 + font_size*0.7.
                    # Current code was just +8. Let's stick to current unless distance is specified?
                    # Or standardize it.
                    # Let's standardize: dist = height/2 + 5.
                    # Top: y - dist.
                    # Bottom: y + dist + font_size*0.7.
                    
                    # But I don't want to break existing look too much if it was fine.
                    # User complaint is about "specified distance".
                    pass

                self._render_text(text, final_x, final_y, font_style=font)

            if switch.label_top:
                # default distance approx
                dist_top = switch.height/2 + 5
                # Pass as negative dy for identification
                render_toggle_label(switch.label_top, "", (0, -dist_top))
                
            if switch.label_bottom:
                # default distance approx
                dist_bot = switch.height/2 + 5 # use 5 padding like top
                # But we need to account for font height for baseline
                # render_toggle_label will handle it if I pass positive dy
                # Wait, render_toggle_label logic above for default:
                # "Let's stick to current unless distance is specified" -> I put 'pass' there.
                # I should implement the standard logic there for consistency.
                
                # Re-do render_toggle_label logic inline for clarity
                pass

            # Refactored toggle label rendering
            if switch.label_top:
                font = switch.label_top.font if switch.label_top.font else default_font_style
                f_size = self._get_font_size_mm(font)
                dist = switch.label_top.distance if switch.label_top.distance is not None else (switch.height/2 + 5)
                # Top label: bottom of text at dist. Baseline at y - dist.
                self._render_text(switch.label_top.text, x, y - dist, font_style=font)

            if switch.label_bottom:
                font = switch.label_bottom.font if switch.label_bottom.font else default_font_style
                f_size = self._get_font_size_mm(font)
                dist = switch.label_bottom.distance if switch.label_bottom.distance is not None else (switch.height/2 + 5)
                # Bottom label: top of text at dist. Baseline at y + dist + ascent.
                self._render_text(switch.label_bottom.text, x, y + dist + f_size * 0.7, font_style=font)

            if switch.label_center:
                font = switch.label_center.font if switch.label_center.font else default_font_style
                # Center label to the right
                dist_x = switch.label_center.distance if switch.label_center.distance is not None else (switch.width/2 + 8)
                # Vertical align middle? SVG text is baseline. 
                # Approx middle by shifting down by 0.35 * font_size
                f_size = self._get_font_size_mm(font)
                self._render_text(switch.label_center.text, x + dist_x, y + f_size * 0.35, font_style=font)


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
                    if i < len(s.labels):
                        label_obj = s.labels[i]
                        label_text = label_obj.text
                        lx = x + label_anchor_radius * math.cos(angle_rad)
                        ly = y + label_anchor_radius * math.sin(angle_rad)
                        
                        # Use label-specific font or fallback to switch default font
                        default_font_style = self._get_element_font(switch)
                        font_style = label_obj.font if label_obj.font else default_font_style
                        
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
            font_style = self._get_element_font(switch)
            font_size = self._get_font_size_mm(font_style)
            
            # Distance logic for toggle vs rotary
            if switch.switch_type == 'rotary':
                 # calculate max radius used by scale/labels
                 # Simplify: knob/2 + tick size + padding + label space
                 dist = switch.knob_diameter/2 + 5 
                 if switch.scale:
                     dist += switch.scale.tick_size + 5
            else:
                 dist = switch.height/2 + 10 # toggle height based
            
            if switch.label.distance is not None:
                dist = switch.label.distance

            if pos == 'top':
                 label_y = y - dist
            else:
                 label_y = y + dist + font_size * 0.7
            
            self._render_text(switch.label.text, x, label_y, font_style=font_style)

    def _render_custom(self, custom: Custom, x: float, y: float):
        component_opacity = 0.5 if self._is_both_mode() else 1.0
        
        # Drill pattern
        if self._should_show_drill():
             self._render_drill_pattern(x, y, mount=custom)

        # Component Visual
        if self._should_show_component():
            if custom.mount:
                if custom.mount.diameter:
                    r = custom.mount.diameter / 2
                    # Generic circle style
                    self.dwg.add(self.dwg.circle(center=(x, y), r=r, 
                                                 fill='#eeeeee', stroke='black', stroke_width=1, opacity=component_opacity))
                    # Add an X to denote generic
                    cross_r = r * 0.7
                    self.dwg.add(self.dwg.line(start=(x - cross_r, y - cross_r), end=(x + cross_r, y + cross_r), 
                                               stroke='black', stroke_width=1, opacity=component_opacity))
                    self.dwg.add(self.dwg.line(start=(x + cross_r, y - cross_r), end=(x - cross_r, y + cross_r), 
                                               stroke='black', stroke_width=1, opacity=component_opacity))

                elif custom.mount.width and custom.mount.height:
                    w = custom.mount.width
                    h = custom.mount.height
                    self.dwg.add(self.dwg.rect(insert=(x - w/2, y - h/2), size=(w, h),
                                               fill='#eeeeee', stroke='black', stroke_width=1, opacity=component_opacity))
                    # Add an X
                    self.dwg.add(self.dwg.line(start=(x - w/2, y - h/2), end=(x + w/2, y + h/2),
                                               stroke='black', stroke_width=1, opacity=component_opacity))
                    self.dwg.add(self.dwg.line(start=(x + w/2, y - h/2), end=(x - w/2, y + h/2),
                                               stroke='black', stroke_width=1, opacity=component_opacity))

        # Label
        if custom.label and custom.label.text:
            # Default to bottom if not specified
            pos = custom.label.position if custom.label.position else 'bottom'
            font_style = self._get_element_font(custom)
            font_size = self._get_font_size_mm(font_style)
            
            # Estimate distance based on mount size
            dist = 10.0 # fallback
            if custom.mount:
                if custom.mount.diameter:
                    dist = custom.mount.diameter / 2 + 5
                elif custom.mount.height:
                    dist = custom.mount.height / 2 + 5
            
            if custom.label.distance is not None:
                dist = custom.label.distance

            if pos == 'top':
                 label_y = y - dist
            else:
                 label_y = y + dist + font_size * 0.7
            
            self._render_text(custom.label.text, x, label_y, font_style=font_style)

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
