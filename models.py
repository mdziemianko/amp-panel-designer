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
            return float(val[:-2]) * (25.4 / 72.0)
        elif val.endswith('px'):
            return float(val[:-2]) * (25.4 / 96.0)
        else:
            try:
                return float(val)
            except ValueError:
                return value
    return value

DIMENSION_KEYS = {'x', 'y', 'width', 'height', 'radius', 'thickness', 'font_size', 'size', 
                  'knob_diameter', 'border_diameter', 'border_thickness', 'tick_size',
                  'install_diameter', 'mount_width', 'mount_height'}

def normalize_data(data: dict) -> dict:
    new_data = data.copy()
    for key, value in new_data.items():
        if key in DIMENSION_KEYS:
            new_data[key] = to_mm(value)
    return new_data

@dataclass
class FontStyle:
    size: Optional[float] = None
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
    label_position: Optional[str] = None 
    font_style: Optional[FontStyle] = None

    @staticmethod
    def from_dict(data: dict):
        data = normalize_data(data)
        
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
            obj = Switch.from_dict(data)
        else:
            raise ValueError(f"Unknown element type: {element_type}")
        
        if font_dict:
            font_dict = normalize_data(font_dict) 
            obj.font_style = FontStyle(**_filter_args(FontStyle, font_dict))
            
        return obj

def _filter_args(cls, data):
    import inspect
    sig = inspect.signature(cls)
    return {k: v for k, v in data.items() if k in sig.parameters}

@dataclass
class Component(Element):
    install_diameter: float = 0.0 

@dataclass
class Scale:
    num_ticks: int = 11
    major_tick_interval: int = 1
    tick_style: str = "line"
    tick_size: float = 2.0
    position: str = "outside"

@dataclass
class Potentiometer(Component):
    knob_diameter: float = 20.0
    border_diameter: float = 25.0
    border_thickness: float = 0.0
    angle_start: float = 45.0
    angle_width: float = 270.0
    scale: Optional[Scale] = None
    install_diameter: float = 6.0
    radius: Optional[float] = None

    @staticmethod
    def from_dict(data: dict):
        scale_data = data.pop('scale', None)
        
        if 'radius' in data and 'knob_diameter' not in data:
             data['knob_diameter'] = data['radius'] * 2.0
        
        pot = Potentiometer(**_filter_args(Potentiometer, data))
        
        if scale_data:
            if isinstance(scale_data, dict):
                scale_data = normalize_data(scale_data)
                pot.scale = Scale(**_filter_args(Scale, scale_data))
        
        return pot

@dataclass
class Socket(Component):
    radius: float = 10.0
    install_diameter: float = 10.0

@dataclass
class Switch(Component):
    switch_type: str = "toggle" # toggle, rotary
    
    width: float = 10.0
    height: float = 20.0
    knob_diameter: float = 20.0 # for rotary
    
    mounting_type: str = "circular" # circular, rectangular
    install_diameter: float = 5.0 
    mount_width: float = 5.0 
    mount_height: float = 10.0
    
    label_top: Optional[str] = None
    label_center: Optional[str] = None
    label_bottom: Optional[str] = None
    
    angle_start: float = 45.0
    angle_width: float = 270.0
    scale: Optional[Scale] = None
    scale_labels: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict):
        scale_data = data.pop('scale', None)
        scale_labels = data.pop('scale_labels', [])
        
        obj = Switch(**_filter_args(Switch, data))
        obj.scale_labels = scale_labels
        
        if scale_data:
            if isinstance(scale_data, dict):
                scale_data = normalize_data(scale_data)
                obj.scale = Scale(**_filter_args(Scale, scale_data))
        
        return obj

@dataclass
class Border:
    type: str = "none" 
    thickness: float = 1.0
    style: str = "full" 
    color: str = "black"

@dataclass
class Group(Element):
    elements: List[Element] = field(default_factory=list)
    width: Optional[float] = None
    height: Optional[float] = None
    border: Optional[Border] = None

    @staticmethod
    def from_dict(data: dict):
        elements_data = data.pop('elements', [])
        border_data = data.pop('border', None)
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
    render_mode: str = "both"

    @staticmethod
    def from_dict(data: dict):
        data = normalize_data(data)
        elements_data = data.pop('elements', [])
        clean_data = _filter_args(Panel, data)
        panel = Panel(**clean_data)
        for el_data in elements_data:
            panel.elements.append(Element.from_dict(el_data))
        return panel
