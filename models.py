from dataclasses import dataclass, field
from typing import List, Optional, Union

@dataclass
class Element:
    id: str
    x: float
    y: float
    type: str
    label: Optional[str] = None

    @staticmethod
    def from_dict(data: dict):
        element_type = data.get('type')
        if element_type == 'group':
            return Group.from_dict(data)
        elif element_type == 'potentiometer':
            return Potentiometer(**_filter_args(Potentiometer, data))
        elif element_type == 'socket':
            return Socket(**_filter_args(Socket, data))
        elif element_type == 'switch':
            return Switch(**_filter_args(Switch, data))
        else:
            raise ValueError(f"Unknown element type: {element_type}")

def _filter_args(cls, data):
    import inspect
    sig = inspect.signature(cls)
    return {k: v for k, v in data.items() if k in sig.parameters}

@dataclass
class Component(Element):
    pass

@dataclass
class Potentiometer(Component):
    scale: Optional[str] = None
    # Diameter or style could be added here
    radius: float = 15.0

@dataclass
class Socket(Component):
    # e.g., 6.3mm jack
    radius: float = 10.0

@dataclass
class Switch(Component):
    # Toggle switch
    width: float = 10.0
    height: float = 20.0

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
        
        clean_data = _filter_args(Group, data)
        group = Group(**clean_data)
        
        if border_data:
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

    @staticmethod
    def from_dict(data: dict):
        elements_data = data.pop('elements', [])
        clean_data = _filter_args(Panel, data)
        panel = Panel(**clean_data)
        for el_data in elements_data:
            panel.elements.append(Element.from_dict(el_data))
        return panel
