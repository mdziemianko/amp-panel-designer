import svgwrite
import math
from typing import Optional, Tuple
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
                font_size = 12 * 25.4 / 72.0 # fallback 12pt
        return len(text) * font_size * 0.6

    def _get_font_size_mm(self, font_style: Optional[FontStyle], default_mm=None) -> float:
        # Default to 12pt (~4.233mm) if not specified
        if default_mm is None:
            default_mm = 12 * 25.4 / 72.0

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

    def _parse_position(self, pos: str) -> Tuple[str, str]:
        """Parses position string like 'top-outside' into ('top', 'outside')."""
        if not pos:
            return 'bottom', 'outside' # default
        parts = pos.split('-')
        side = parts[0]
        mode = parts[1] if len(parts) > 1 else 'outside'
        
        # Normalize side for group shortcuts if any, though existing map is explicit
        return side, mode

    def _render_group(self, elements: list[Element], offset_x: float, offset_y: float):
        for element in elements:
            abs_x = offset_x + element.x
            abs_y = offset_y + element.y
            
            if isinstance(element, Group):
                label_gap = None
                label_gap_side = None # 'top', 'bottom', 'left', 'right'
                
                # Render group label if exists
                if element.label and element.label.text:
                    label_text = element.label.text
                    
                    font_style = self._get_element_font(element)
                    
                    default_size = 12 * 25.4 / 72.0
                    size = font_style.size if font_style and font_style.size else default_size
                    
                    # Convert font size to mm
                    try:
                        if isinstance(size, str):
                             val = size.lower().replace("pt", "").replace("px", "").replace("mm", "")
                             size_val = float(val)
                        else:
                             size_val = float(size)
                    except ValueError:
                        size_val = default_size

                    raw_pos = element.label.position if element.label.position else 'top-outside'
                    side, mode = self._parse_position(raw_pos)

                    text_width = self._get_text_width(label_text, size_val)
                    
                    # Defaults
                    label_x = abs_x
                    label_y = abs_y
                    anchor = 'middle'

                    # Calculate positions
                    if side == 'center':
                        label_x = abs_x + (element.width / 2 if element.width else 0)
                        label_y = abs_y + (element.height / 2 if element.height else 0) + size_val * 0.35 # vertical center approx
                        anchor = 'middle'
                    
                    elif side == 'top':
                        label_x = abs_x + (element.width / 2 if element.width else 0)
                        if mode == 'inline':
                            label_y = abs_y + size_val * 0.35 
                            label_gap = (label_x - text_width/2 - 2, label_x + text_width/2 + 2)
                            label_gap_side = 'top'
                        elif mode == 'inside':
                            label_y = abs_y + size_val + 2
                        else: # outside
                            label_y = abs_y - 5
                    
                    elif side == 'bottom':
                        label_x = abs_x + (element.width / 2 if element.width else 0)
                        base_y = abs_y + (element.height if element.height else 0)
                        if mode == 'inline':
                            label_y = base_y + size_val * 0.35
                            label_gap = (label_x - text_width/2 - 2, label_x + text_width/2 + 2)
                            label_gap_side = 'bottom'
                        elif mode == 'inside':
                            label_y = base_y - 5
                        else: # outside
                            label_y = base_y + size_val + 2
                            
                    elif side == 'left':
                        label_y = abs_y + (element.height / 2 if element.height else 0) + size_val * 0.35
                        if mode == 'inline':
                            label_x = abs_x
                            # Gap on vertical line: y-coordinates
                            # text_width is horizontal width. 
                            # Since we don't rotate text for now, the gap logic for left/right inline needs checking.
                            # Usually side labels are rotated? If not, they just sit on the line.
                            # If text is horizontal, it will cross the line.
                            # gap is (y_start, y_end)
                            # But current logic is horizontal text.
                            # A horizontal text on a vertical line looks weird if inline.
                            # Assuming horizontal text centered on line.
                            # We'll gap the line around the text height? Or text width?
                            # Text crosses line perpendicularly.
                            # We can just gap around the middle.
                            # Gap size = font_size (height) roughly?
                            gap_size = size_val
                            label_gap = (label_y - gap_size/2 - 2, label_y + gap_size/2 + 2) # Vertical gap
                            label_gap_side = 'left'
                            anchor = 'middle'
                        elif mode == 'inside':
                            label_x = abs_x + 5
                            anchor = 'start'
                        else: # outside
                            label_x = abs_x - 5
                            anchor = 'end'

                    elif side == 'right':
                        label_y = abs_y + (element.height / 2 if element.height else 0) + size_val * 0.35
                        base_x = abs_x + (element.width if element.width else 0)
                        if mode == 'inline':
                            label_x = base_x
                            gap_size = size_val
                            label_gap = (label_y - gap_size/2 - 2, label_y + gap_size/2 + 2)
                            label_gap_side = 'right'
                            anchor = 'middle'
                        elif mode == 'inside':
                            label_x = base_x - 5
                            anchor = 'end'
                        else: # outside
                            label_x = base_x + 5
                            anchor = 'start'

                    self._render_text(label_text, label_x, label_y, default_size=default_size, default_weight='normal', font_style=font_style, anchor=anchor)

                self._render_border(element, abs_x, abs_y, label_gap=label_gap, label_gap_side=label_gap_side)
                self._render_group(element.elements, abs_x, abs_y)
            
            elif isinstance(element, Potentiometer):
                self._render_potentiometer(element, abs_x, abs_y)
            
            elif isinstance(element, Socket):
                self._render_socket(element, abs_x, abs_y)
            
            elif isinstance(element, Switch):
                self._render_switch(element, abs_x, abs_y)

            elif isinstance(element, Custom):
                self._render_custom(element, abs_x, abs_y)

    def _render_border(self, group: Group, x: float, y: float, label_gap=None, label_gap_side=None):
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

        def draw_line_with_gap(x1, y1, x2, y2, gap, is_vertical=False):
            if not gap:
                draw_line(x1, y1, x2, y2)
                return
            
            gap_start, gap_end = gap
            # Normalize gap direction
            if is_vertical:
                # Line is vertical, x1==x2. coordinate of interest is y.
                start_coord = min(y1, y2)
                end_coord = max(y1, y2)
                
                # Draw segments
                if gap_start > start_coord:
                    draw_line(x1, start_coord, x1, gap_start)
                if gap_end < end_coord:
                    draw_line(x1, gap_end, x1, end_coord)
            else:
                # Horizontal
                start_coord = min(x1, x2)
                end_coord = max(x1, x2)
                
                if gap_start > start_coord:
                    draw_line(start_coord, y1, gap_start, y1)
                if gap_end < end_coord:
                    draw_line(gap_end, y1, end_coord, y1)

        # Edges
        # Top
        if b.type in ('full', 'top'):
            if label_gap_side == 'top':
                draw_line_with_gap(x, y, x + group.width, y, label_gap, is_vertical=False)
            else:
                draw_line(x, y, x + group.width, y)
        
        # Bottom
        if b.type in ('full', 'bottom'):
            if label_gap_side == 'bottom':
                draw_line_with_gap(x, y + group.height, x + group.width, y + group.height, label_gap, is_vertical=False)
            else:
                draw_line(x, y + group.height, x + group.width, y + group.height)
                
        # Left and Right (only for full border usually? or if user asks for specific sides later. Currently full or top/bottom)
        # But wait, Group border type is 'none', 'full', 'top', 'bottom'.
        # If 'full', we draw sides.
        if b.type == 'full':
            # Left
            if label_gap_side == 'left':
                draw_line_with_gap(x, y, x, y + group.height, label_gap, is_vertical=True)
            else:
                draw_line(x, y, x, y + group.height)
            
            # Right
            if label_gap_side == 'right':
                draw_line_with_gap(x + group.width, y, x + group.width, y + group.height, label_gap, is_vertical=True)
            else:
                draw_line(x + group.width, y, x + group.width, y + group.height)


    def _calculate_label_pos(self, x, y, side, mode, dist, font_size, text_width=0) -> Tuple[float, float, str]:
        """Calculates (lx, ly, anchor) for a component label."""
        # Default behavior (outside)
        lx, ly = x, y
        anchor = 'middle'
        
        if side == 'top':
            if mode == 'inside':
                 # Inside component boundary? 
                 # For components, "inside" might mean below top edge of bounding box?
                 # Or just closer to center than outside.
                 # Let's interpret 'inside' as: center - dist
                 # Wait, 'top-outside' means above center by dist.
                 # 'top-inside' usually means below top border, so closer to center?
                 # If we treat 'dist' as distance from center:
                 ly = y - dist
            elif mode == 'inline':
                 ly = y - dist # On the edge?
            else: # outside
                 ly = y - dist
                 
            # Adjust for baseline if needed.
            # Usually top label baseline is y - dist.
            
        elif side == 'bottom':
            ly = y + dist + font_size * 0.7
            
        elif side == 'left':
            lx = x - dist
            ly = y + font_size * 0.35
            anchor = 'end'
            if mode == 'inside':
                 anchor = 'start'
                 lx = x - dist + text_width # ? No.
                 # If left-inside, it's inside the left edge.
                 # Since components are usually centered at x,y with radius/width.
                 # dist is typically from center.
                 # So left-inside would be x - dist (closer to center?)
                 # Actually for components, "inside/outside" relative to a border ring:
                 # Outside: > radius. Inside: < radius.
                 # If user supplies 'distance', we use it.
                 pass

        elif side == 'right':
            lx = x + dist
            ly = y + font_size * 0.35
            anchor = 'start'
            if mode == 'inside':
                 anchor = 'end'
                 pass
        
        return lx, ly, anchor

    def _render_component_label(self, element: Component, x: float, y: float, default_dist: float):
        if element.label and element.label.text:
            raw_pos = element.label.position if element.label.position else 'bottom-outside'
            side, mode = self._parse_position(raw_pos)
            
            font_style = self._get_element_font(element)
            font_size = self._get_font_size_mm(font_style)
            
            dist = default_dist
            if element.label.distance is not None:
                dist = element.label.distance
            
            # Calculate coordinates
            lx, ly = x, y
            anchor = 'middle'
            
            if side == 'top':
                # Dist is up
                ly = y - dist
                # If inline, maybe adjust?
            
            elif side == 'bottom':
                # Dist is down
                ly = y + dist + font_size * 0.7
            
            elif side == 'left':
                lx = x - dist
                ly = y + font_size * 0.35 # Vertically centered
                anchor = 'end'
                if mode == 'inside':
                    anchor = 'start' # ? If inside left edge, text starts there?
                    # Or 'end' but position is diff?
                    # Let's keep it simple: left-outside is default.
                elif mode == 'inline':
                    anchor = 'middle' # Centered on the line?

            elif side == 'right':
                lx = x + dist
                ly = y + font_size * 0.35
                anchor = 'start'
                if mode == 'inside':
                    anchor = 'end'
                elif mode == 'inline':
                    anchor = 'middle'
            
            elif side == 'center':
                 ly = y + font_size * 0.35
                 anchor = 'middle'

            self._render_text(element.label.text, lx, ly, font_style=font_style, anchor=anchor)

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
                
                # Determine base radius based on scale position
                border_r = (pot.border_diameter / 2)
                
                if s.position == 'outside':
                    tick_r_start = border_r + 1.0 # Standard gap outside
                elif s.position == 'inside':
                    tick_r_start = border_r - 1.0 # Start inside border
                elif s.position == 'inline':
                    # This means centered on the border line
                    # Wait, we need tick_r_start and current_tick_len.
                    # If inline, we draw across the border.
                    # Let's handle it inside loop per tick length.
                    pass
                else:
                    # Fallback logic if position is invalid or default 'outside' logic
                    base_radius = (pot.border_diameter / 2) if pot.border_diameter > pot.knob_diameter else (pot.knob_diameter / 2)
                    tick_r_start = base_radius + 1.0 

                for i in range(s.num_ticks):
                    angle_user = start_angle_user + i * step
                    angle_svg_deg = angle_user + 90
                    angle_rad = math.radians(angle_svg_deg)
                    
                    is_major = (i % s.major_tick_interval == 0) if s.major_tick_interval > 0 else True
                    
                    current_tick_len = s.tick_size if is_major else s.tick_size * 0.5
                    
                    # Calculate start/end based on position
                    if s.position == 'outside':
                        r_start = tick_r_start
                        r_end = r_start + current_tick_len
                    elif s.position == 'inside':
                        r_start = tick_r_start
                        r_end = r_start - current_tick_len
                    elif s.position == 'inline':
                        r_start = border_r - (current_tick_len / 2)
                        r_end = border_r + (current_tick_len / 2)
                    else: # Legacy/default behavior
                        r_start = tick_r_start
                        r_end = r_start + current_tick_len

                    x1 = x + r_start * math.cos(angle_rad)
                    y1 = y + r_start * math.sin(angle_rad)
                    
                    if s.tick_style == 'dot':
                        r_dot = (current_tick_len / 2) if is_major else (current_tick_len * 0.5 / 2) # Minor tick dot radius is 50% of major
                        # Center of dot
                        if s.position == 'inside':
                             # center at r_start - r_dot
                             r_center = r_start - r_dot
                        elif s.position == 'inline':
                             r_center = border_r
                        else:
                             # outside: r_start + r_dot
                             r_center = r_start + r_dot
                             
                        x_dot = x + r_center * math.cos(angle_rad)
                        y_dot = y + r_center * math.sin(angle_rad)
                        
                        self.dwg.add(self.dwg.circle(center=(x_dot, y_dot), r=r_dot, fill='black'))
                    else: # line
                        x2 = x + r_end * math.cos(angle_rad)
                        y2 = y + r_end * math.sin(angle_rad)
                        self.dwg.add(self.dwg.line(start=(x1, y1), end=(x2, y2), stroke='black', stroke_width=1 if not is_major else 1.5))

        if self._should_show_component():
            self.dwg.add(self.dwg.circle(center=(x, y), r=knob_radius, fill='white', stroke='black', stroke_width=1, opacity=component_opacity))
            self.dwg.add(self.dwg.line(start=(x, y), end=(x, y - knob_radius + 2), stroke='black', stroke_width=2, opacity=component_opacity))
            
        # Label
        # Default distance calculation
        outer_radius = (pot.border_diameter / 2)
        if pot.scale:
            outer_radius += pot.scale.tick_size + 2
        default_dist = max(outer_radius, pot.knob_diameter/2) + 2 
        
        self._render_component_label(pot, x, y, default_dist)

    def _render_socket(self, socket: Socket, x: float, y: float):
        component_opacity = 0.5 if self._is_both_mode() else 1.0
        
        if self._should_show_drill():
             self._render_drill_pattern(x, y, mount=socket)

        if self._should_show_component():
            self.dwg.add(self.dwg.circle(center=(x, y), r=socket.radius, fill='#333333', stroke='black', stroke_width=1, opacity=component_opacity))
            self.dwg.add(self.dwg.circle(center=(x, y), r=socket.radius/2, fill='black', opacity=component_opacity))
        
        default_dist = socket.radius + 5
        self._render_component_label(socket, x, y, default_dist)

    def _render_switch(self, switch: Switch, x: float, y: float):
        component_opacity = 0.5 if self._is_both_mode() else 1.0
        
        # Drill pattern
        if self._should_show_drill():
             self._render_drill_pattern(x, y, mount=switch)

        # Switch Labels (Top/Center/Bottom)
        if switch.switch_type == 'toggle':
            # Render labels always (printed)
            default_font_style = self._get_element_font(switch)
            
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
                        r_dot = (current_tick_len / 2) if is_major else (current_tick_len * 0.5 / 2) # Minor tick dot radius is 50% of major
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
                        
                        self._render_text(label_text, lx, ly + 1.5, font_style=font_style)

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
        # Distance logic for toggle vs rotary
        if switch.switch_type == 'rotary':
             # calculate max radius used by scale/labels
             # Simplify: knob/2 + tick size + padding + label space
             dist = switch.knob_diameter/2 + 5 
             if switch.scale:
                 dist += switch.scale.tick_size + 5
        else:
             dist = switch.height/2 + 10 # toggle height based
        
        self._render_component_label(switch, x, y, dist)

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
        # Estimate distance based on mount size
        dist = 10.0 # fallback
        if custom.mount:
            if custom.mount.diameter:
                dist = custom.mount.diameter / 2 + 5
            elif custom.mount.height:
                dist = custom.mount.height / 2 + 5
        
        self._render_component_label(custom, x, y, dist)

    def _render_text(self, text: str, x: float, y: float, default_size=None, default_weight='normal', font_style: FontStyle = None, anchor="middle"):
        if default_size is None:
            default_size = 12 * 25.4 / 72.0
            
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
                                   text_anchor=anchor, 
                                   font_family=family, 
                                   font_size=size,
                                   font_weight=weight,
                                   fill=color))
