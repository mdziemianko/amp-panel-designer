from dataclasses import dataclass, field
from typing import List, Optional, Union

def to_mm(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        val = value.strip().lower()
        if val.endswith('mm'):
            return float(val[:-2])
        elif val.endswith('cm'):
            return float(val[:-2]) * 10.0
        elif val.endswith('in'):
            return float(val[:-2]) * 25.4
        elif val.endswith('"'):
            return float(val[:-1]) * 25.4
        elif val.endswith('pt'):
            # 1 pt = 1/72 inch = 25.4 / 72 mm approx 0.352778 mm
            return float(val[:-2]) * (25.4 / 72.0)
        elif val.endswith('px'):
            # 1 px = 1/96 inch = 25.4 / 96 mm approx 0.264583 mm
            return float(val[:-2]) * (25.4 / 96.0)
        else:
            try:
                return float(val)
            except ValueError:
                # Return original if parsing fails, let validation downstream handle it or it might be a non-numeric string meant for something else (though we filter keys)
                return value
    return value

DIMENSION_KEYS = {'x', 'y', 'width', 'height', 'radius', 'thickness', 'font_size', 'size', 
                  'knob_diameter', 'border_diameter', 'border_thickness', 'tick_size',
                  'install_diameter'}

def normalize_data(data: dict) -> dict:
    new_data = data.copy()
    for key, value in new_data.items():
        if key in DIMENSION_KEYS:
            new_data[key] = to_mm(value)
    return new_data

@dataclass
class FontStyle:
    size: Optional[float] = None # in mm or points? SVG standard default is usually px, here we treat numbers as user units
    color: Optional[str] = None
    family: Optional[str] = None
    weight: Optional[str] = None

@dataclass
class Element:
    id: str
    x: float
    y: float
    type: str
    label: Optional[str] = None
    label_position: Optional[str] = None # top, bottom, etc.
    font_style: Optional[FontStyle] = None

    @staticmethod
    def from_dict(data: dict):
        # We normalize here for base properties like x, y
        data = normalize_data(data)
        
        # Extract font style
        font_data = data.pop('font_style', None)
        font_dict = data.pop('font', None)

        element_type = data.get('type')
        if element_type == 'group':
            obj = Group.from_dict(data)
        elif element_type == 'potentiometer':
            obj = Potentiometer.from_dict(data)
        elif element_type == 'socket':
            obj = Socket(**_filter_args(Socket, data))
        elif element_type == 'switch':
            obj = Switch(**_filter_args(Switch, data))
        else:
            raise ValueError(f"Unknown element type: {element_type}")
        
        if font_dict:
            font_dict = normalize_data(font_dict) # normalize font_size if present
            obj.font_style = FontStyle(**_filter_args(FontStyle, font_dict))
            
        return obj

def _filter_args(cls, data):
    import inspect
    sig = inspect.signature(cls)
    return {k: v for k, v in data.items() if k in sig.parameters}

@dataclass
class Component(Element):
    install_diameter: float = 0.0 # Will be set by subclasses default

@dataclass
class Scale:
    num_ticks: int = 11
    major_tick_interval: int = 1
    tick_style: str = "line" # "line" or "dot"
    tick_size: float = 2.0
    position: str = "outside" # relative to border? Or just standard position.

@dataclass
class Potentiometer(Component):
    knob_diameter: float = 20.0
    border_diameter: float = 25.0
    border_thickness: float = 0.0
    angle_start: float = 45.0 # User degrees: 0 down, clockwise
    angle_width: float = 270.0
    scale: Optional[Scale] = None
    install_diameter: float = 6.0
    
    # Deprecated/Mapped
    radius: Optional[float] = None # Old field

    @staticmethod
    def from_dict(data: dict):
        scale_data = data.pop('scale', None)
        
        # Map old radius to knob_diameter if present and no knob_diameter
        if 'radius' in data and 'knob_diameter' not in data:
             # radius was 15.0 (30mm dia) default in old code, new default is 20mm.
             # If user provided radius, use it.
             data['knob_diameter'] = data['radius'] * 2.0
        
        # clean_data = _filter_args(Potentiometer, data)
        # pot = Potentiometer(**clean_data)
        # We use standard constructor via filter_args
        
        # Need to handle nested scale object
        pot = Potentiometer(**_filter_args(Potentiometer, data))
        
        if scale_data:
            if isinstance(scale_data, dict):
                scale_data = normalize_data(scale_data)
                pot.scale = Scale(**_filter_args(Scale, scale_data))
            elif isinstance(scale_data, str):
                pass
        
        return pot

@dataclass
class Socket(Component):
    # e.g., 6.3mm jack
    radius: float = 10.0
    install_diameter: float = 10.0

@dataclass
class Switch(Component):
    # Toggle switch
    width: float = 10.0
    height: float = 20.0
    install_diameter: float = 5.0

@dataclass
class Border:
    type: str = "none" # none, full, top, bottom
    thickness: float = 1.0
    style: str = "full" # full, dotted, dashed
    color: str = "black"

@dataclass
class Group(Element):
    elements: List[Element] = field(default_factory=list)
    width: Optional[float] = None
    height: Optional[float] = None
    border: Optional[Border] = None

    @staticmethod
    def from_dict(data: dict):
        # specific handling for recursion
        elements_data = data.pop('elements', [])
        border_data = data.pop('border', None)
        
        # data is already normalized if coming from Element.from_dict, but safe to do again or for Group specific props
        data = normalize_data(data)
        
        clean_data = _filter_args(Group, data)
        group = Group(**clean_data)
        
        if border_data:
            border_data = normalize_data(border_data)
            group.border = Border(**_filter_args(Border, border_data))
            
        for el_data in elements_data:
            group.elements.append(Element.from_dict(el_data))
        return group

@dataclass
class Panel:
    name: str
    width: float
    height: float
    elements: List[Element] = field(default_factory=list)
    background_color: str = "#ffffff"
    render_mode: str = "both" # show, hide, both

    @staticmethod
    def from_dict(data: dict):
        data = normalize_data(data)
        elements_data = data.pop('elements', [])
        clean_data = _filter_args(Panel, data)
        panel = Panel(**clean_data)
        for el_data in elements_data:
            panel.elements.append(Element.from_dict(el_data))
        return panel
