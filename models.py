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
                  'install_diameter', 'mount_width', 'mount_height', 'diameter'}

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
class Label:
    text: str
    position: Optional[str] = None
    font: Optional[FontStyle] = None

@dataclass
class Mount:
    diameter: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None

@dataclass
class Element:
    id: str
    x: float
    y: float
    type: str
    label: Optional[Label] = None
    font_style: Optional[FontStyle] = None

    @staticmethod
    def _parse_label_param(value) -> Optional[Label]:
        if value is None:
            return None
        if isinstance(value, str):
            return Label(text=value)
        if isinstance(value, dict):
            value = normalize_data(value)
            lbl_font_dict = value.pop('font', None)
            lbl_font = None
            if lbl_font_dict:
                lbl_font_dict = normalize_data(lbl_font_dict)
                lbl_font = FontStyle(**_filter_args(FontStyle, lbl_font_dict))
            
            lbl_text = value.pop('text', "")
            lbl_pos = value.pop('position', None)
            return Label(text=lbl_text, position=lbl_pos, font=lbl_font)
        return None

    @staticmethod
    def from_dict(data: dict):
        data = normalize_data(data)
        
        font_data = data.pop('font_style', None)
        font_dict = data.pop('font', None)
        
        # Parse label
        label_data = data.pop('label', None)
        label_position = data.pop('label_position', None)
        
        element_type = data.get('type')
        if element_type == 'group':
            obj = Group.from_dict(data)
        elif element_type == 'potentiometer':
            obj = Potentiometer.from_dict(data)
        elif element_type == 'socket':
            obj = Socket.from_dict(data)
        elif element_type == 'switch':
            obj = Switch.from_dict(data)
        else:
            raise ValueError(f"Unknown element type: {element_type}")
        
        # Handle Font at root (applies to Element.font_style)
        if font_dict:
            font_dict = normalize_data(font_dict) 
            obj.font_style = FontStyle(**_filter_args(FontStyle, font_dict))
            
        # Handle Label (Main)
        if label_data:
            # Re-use _parse_label_param but handle legacy label_position merging
            parsed = Element._parse_label_param(label_data)
            if parsed:
                 if not parsed.position and label_position:
                      parsed.position = label_position
                 obj.label = parsed
        elif label_position:
             # Just position? Probably redundant without text, but legacy might expect label=""?
             # Old code handled `label: str` with separate `label_position`
             # If label is missing, user might just have label_position but no text?
             pass

        return obj

def _filter_args(cls, data):
    import inspect
    sig = inspect.signature(cls)
    return {k: v for k, v in data.items() if k in sig.parameters}

@dataclass
class Component(Element):
    mount: Optional[Mount] = None
    
    def __post_init__(self):
        # Validate mount configuration if present
        if self.mount:
             if self.mount.diameter is not None:
                 if self.mount.width is not None or self.mount.height is not None:
                      raise ValueError(f"Component {self.id}: Cannot specify both diameter and width/height in mount.")
             else:
                 if self.mount.width is None or self.mount.height is None:
                      raise ValueError(f"Component {self.id}: Must specify either diameter OR (width and height) in mount.")

    @staticmethod
    def _parse_mount(data: dict, default_diameter=None) -> Optional[Mount]:
        mount_data = data.pop('mount', None)
        
        # Legacy mapping for backward compatibility
        install_diameter = data.pop('install_diameter', None)
        mount_width = data.pop('mount_width', None)
        mount_height = data.pop('mount_height', None)
        mounting_type = data.pop('mounting_type', None) # Consume but ignore logic, use params instead

        if mount_data:
            mount_data = normalize_data(mount_data)
            return Mount(**_filter_args(Mount, mount_data))
        
        # If no mount block, check legacy fields
        if install_diameter is not None:
             install_diameter = to_mm(install_diameter)
             return Mount(diameter=install_diameter)
        elif mount_width is not None and mount_height is not None:
             return Mount(width=to_mm(mount_width), height=to_mm(mount_height))
        
        # Default
        if default_diameter is not None:
             return Mount(diameter=default_diameter)
             
        return None

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
    radius: Optional[float] = None

    @staticmethod
    def from_dict(data: dict):
        scale_data = data.pop('scale', None)
        
        if 'radius' in data and 'knob_diameter' not in data:
             data['knob_diameter'] = data['radius'] * 2.0
        
        # Parse mount before creating object to remove keys from data
        mount = Component._parse_mount(data, default_diameter=6.0)
        
        pot = Potentiometer(**_filter_args(Potentiometer, data))
        pot.mount = mount
        
        if scale_data:
            if isinstance(scale_data, dict):
                scale_data = normalize_data(scale_data)
                pot.scale = Scale(**_filter_args(Scale, scale_data))
        
        return pot

@dataclass
class Socket(Component):
    radius: float = 10.0
    
    @staticmethod
    def from_dict(data: dict):
        mount = Component._parse_mount(data, default_diameter=10.0)
        obj = Socket(**_filter_args(Socket, data))
        obj.mount = mount
        return obj

@dataclass
class Switch(Component):
    switch_type: str = "toggle" # toggle, rotary
    
    width: float = 10.0
    height: float = 20.0
    knob_diameter: float = 20.0 # for rotary
    
    label_top: Optional[Label] = None
    label_center: Optional[Label] = None
    label_bottom: Optional[Label] = None
    
    angle_start: float = 45.0
    angle_width: float = 270.0
    scale: Optional[Scale] = None
    scale_labels: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict):
        scale_data = data.pop('scale', None)
        scale_labels = data.pop('scale_labels', [])
        
        # Extract new labels using helper
        lt = Element._parse_label_param(data.pop('label_top', None))
        lc = Element._parse_label_param(data.pop('label_center', None))
        lb = Element._parse_label_param(data.pop('label_bottom', None))

        # Default diameter 5.0 for switch
        mount = Component._parse_mount(data, default_diameter=5.0)
        
        obj = Switch(**_filter_args(Switch, data))
        obj.scale_labels = scale_labels
        obj.mount = mount
        obj.label_top = lt
        obj.label_center = lc
        obj.label_bottom = lb
        
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
