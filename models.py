from dataclasses import dataclass, field
from typing import List, Optional, Union

_DPI_PX: float = 96.0  # default CSS px reference

def set_dpi(dpi: Union[int, float]) -> None:
    """Configure DPI used for converting `px` to millimeters."""
    global _DPI_PX
    dpi_f = float(dpi)
    if dpi_f <= 0:
        raise ValueError("dpi must be > 0")
    _DPI_PX = dpi_f

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
            return float(val[:-2]) * (25.4 / _DPI_PX)
        else:
            try:
                return float(val)
            except ValueError:
                return value
    return value

DIMENSION_KEYS = {'x', 'y', 'width', 'height', 'radius', 'thickness', 'font_size', 'size', 
                  'knob_diameter', 'border_diameter', 'border_thickness', 'tick_size',
                  'install_diameter', 'mount_width', 'mount_height', 'diameter', 'distance'}

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
    distance: Optional[float] = None

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
            lbl_dist = value.pop('distance', None)
            return Label(text=lbl_text, position=lbl_pos, font=lbl_font, distance=lbl_dist)
        return None

    @staticmethod
    def from_dict(data: dict):
        data = normalize_data(data)
        
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
        elif element_type == 'custom':
            obj = Custom.from_dict(data)
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
class Custom(Component):
    @staticmethod
    def from_dict(data: dict):
        mount = Component._parse_mount(data)
        obj = Custom(**_filter_args(Custom, data))
        obj.mount = mount
        return obj

@dataclass
class Scale:
    num_ticks: int = 11
    major_tick_interval: int = 1
    tick_style: str = "line"
    tick_size: float = 2.0
    position: str = "outside" # outside, inside, inline
    color: str = "black"
    minor_color: Optional[str] = None  # if unset, same as color
    labels: List[Label] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict):
        labels_data = data.pop('labels', [])
        obj = Scale(**_filter_args(Scale, data))
        
        for item in labels_data:
            parsed = Element._parse_label_param(item)
            if parsed:
                obj.labels.append(parsed)
                
        return obj

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
                pot.scale = Scale.from_dict(scale_data)
        
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

    @staticmethod
    def from_dict(data: dict):
        scale_data = data.pop('scale', None)
        scale_labels = data.pop('scale_labels', []) # Legacy
        
        # Extract new labels using helper
        lt = Element._parse_label_param(data.pop('label_top', None))
        lc = Element._parse_label_param(data.pop('label_center', None))
        lb = Element._parse_label_param(data.pop('label_bottom', None))

        # Default diameter 5.0 for switch
        mount = Component._parse_mount(data, default_diameter=5.0)
        
        obj = Switch(**_filter_args(Switch, data))
        obj.mount = mount
        obj.label_top = lt
        obj.label_center = lc
        obj.label_bottom = lb
        
        if scale_data:
            if isinstance(scale_data, dict):
                scale_data = normalize_data(scale_data)
                obj.scale = Scale.from_dict(scale_data)
        
        # Backward compatibility: merge legacy scale_labels into scale.labels if scale exists, or create scale
        if scale_labels:
            if not obj.scale:
                # If no scale but legacy labels, create a dummy scale? Or just attach?
                # Rotary needs scale object for ticks usually. But if user just had labels?
                # Assume default scale if not present but labels are? Or just ignore if no scale?
                # Let's create default scale if missing, or use existing.
                obj.scale = Scale() # Default values
            
            # Append legacy labels as Label objects
            for lbl_str in scale_labels:
                obj.scale.labels.append(Label(text=str(lbl_str)))
        
        return obj

@dataclass
class BackgroundImage:
    """Raster image drawn behind components (after solid panel color)."""
    path: str
    intrinsic_width: Optional[float] = None   # px; detected via Pillow if omitted
    intrinsic_height: Optional[float] = None
    source_x: float = 0.0
    source_y: float = 0.0
    source_width: float = 1.0
    source_height: float = 1.0
    source_units: str = "normalized"  # "normalized" (0–1 of bitmap) or "pixels"
    fit: str = "cover"  # cover, contain, fill
    zoom: float = 1.0
    pan_x: float = 0.0  # mm in panel space
    pan_y: float = 0.0
    opacity: float = 1.0
    align_horizontal: str = "center"  # left, center, right
    align_vertical: str = "center"  # top, center, bottom

    @staticmethod
    def from_dict(data: dict) -> "BackgroundImage":
        if not isinstance(data, dict):
            raise ValueError("background image must be a mapping")
        data = dict(data)
        path = data.pop("path", None)
        if not path or not isinstance(path, str):
            raise ValueError("background image requires string 'path'")

        def _num(v, default=None):
            if v is None:
                return default
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                return float(v.strip())
            raise TypeError(f"expected number, got {type(v)}")

        src = data.pop("source", None)
        if isinstance(src, dict):
            if "x" in src:
                data.setdefault("source_x", _num(src.get("x")))
            if "y" in src:
                data.setdefault("source_y", _num(src.get("y")))
            if "width" in src:
                data.setdefault("source_width", _num(src.get("width")))
            if "height" in src:
                data.setdefault("source_height", _num(src.get("height")))

        pan = data.pop("pan", None)
        if isinstance(pan, dict):
            if "x" in pan:
                data["pan_x"] = to_mm(pan["x"])
            if "y" in pan:
                data["pan_y"] = to_mm(pan["y"])

        align = data.pop("align", None)
        if isinstance(align, dict):
            h = align.get("horizontal", "center")
            v = align.get("vertical", "center")
            data["align_horizontal"] = str(h).lower()
            data["align_vertical"] = str(v).lower()
        elif isinstance(align, str):
            a = align.strip().lower().replace("-", " ")
            if a in ("center", "middle"):
                data["align_horizontal"] = "center"
                data["align_vertical"] = "center"
            elif a in ("top left", "left top", "top-left"):
                data["align_horizontal"] = "left"
                data["align_vertical"] = "top"
            elif a in ("top right", "right top"):
                data["align_horizontal"] = "right"
                data["align_vertical"] = "top"
            elif a in ("bottom left", "left bottom"):
                data["align_horizontal"] = "left"
                data["align_vertical"] = "bottom"
            elif a in ("bottom right", "right bottom"):
                data["align_horizontal"] = "right"
                data["align_vertical"] = "bottom"
            elif a in ("top", "top center"):
                data["align_horizontal"] = "center"
                data["align_vertical"] = "top"
            elif a in ("bottom", "bottom center"):
                data["align_horizontal"] = "center"
                data["align_vertical"] = "bottom"
            elif a in ("left", "left center", "center left"):
                data["align_horizontal"] = "left"
                data["align_vertical"] = "center"
            elif a in ("right", "right center", "center right"):
                data["align_horizontal"] = "right"
                data["align_vertical"] = "center"

        for key in ("intrinsic_width", "intrinsic_height", "source_x", "source_y",
                    "source_width", "source_height", "zoom", "opacity"):
            if key in data and isinstance(data[key], str):
                try:
                    data[key] = float(data[key].strip())
                except ValueError:
                    pass

        obj = BackgroundImage(path=path, **_filter_args(BackgroundImage, data))

        su = (obj.source_units or "normalized").lower()
        if su not in ("normalized", "pixels"):
            raise ValueError("background_image.source_units must be 'normalized' or 'pixels'")
        obj.source_units = su

        ft = (obj.fit or "cover").lower()
        if ft not in ("cover", "contain", "fill"):
            raise ValueError("background_image.fit must be 'cover', 'contain', or 'fill'")
        obj.fit = ft

        if obj.zoom <= 0:
            raise ValueError("background_image.zoom must be > 0")
        if not (0.0 <= obj.opacity <= 1.0):
            raise ValueError("background_image.opacity must be between 0 and 1")

        for name, allowed in (
            ("align_horizontal", ("left", "center", "right")),
            ("align_vertical", ("top", "center", "bottom")),
        ):
            val = getattr(obj, name).lower()
            if val not in allowed:
                raise ValueError(f"background_image.{name} must be one of {allowed}")
            setattr(obj, name, val)

        if obj.source_units == "normalized":
            if obj.source_width <= 0 or obj.source_height <= 0:
                raise ValueError("normalized source width/height must be > 0")
            for n, v in (("source_x", obj.source_x), ("source_y", obj.source_y)):
                if not (0.0 <= v <= 1.0):
                    raise ValueError(f"normalized {n} must be in [0,1]")
        else:
            if obj.source_width <= 0 or obj.source_height <= 0:
                raise ValueError("background_image source width/height must be > 0 in pixels")

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
    background_image: Optional[BackgroundImage] = None
    render_mode: str = "both"

    @staticmethod
    def from_dict(data: dict):
        data = dict(data)
        bg_block = data.pop("background", None)
        bg_img_data = data.pop("background_image", None)
        if isinstance(bg_block, dict):
            if "color" in bg_block:
                data["background_color"] = bg_block["color"]
            if "image" in bg_block and bg_img_data is None:
                bg_img_data = bg_block["image"]
        data = normalize_data(data)
        elements_data = data.pop("elements", [])
        clean_data = _filter_args(Panel, data)
        panel = Panel(**clean_data)
        if bg_img_data is not None:
            panel.background_image = BackgroundImage.from_dict(bg_img_data)
        for el_data in elements_data:
            panel.elements.append(Element.from_dict(el_data))
        return panel
