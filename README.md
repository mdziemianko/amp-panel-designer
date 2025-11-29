# Panel Maker

A tool to design instrument amplifier panels declaratively using YAML.

## Usage

1. Define your panel in a YAML file (e.g., `panel.yaml`).
2. Run the generator: `python main.py panel.yaml output.svg`.

## Features

- **Components**: Potentiometers, Switches, Sockets.
- **Grouping**: Recursive groups with relative positioning.
- **Styling**: Customizable borders, fonts, and label positioning.
- **Units**: Support for `mm` (default), `cm`, `in` (inches), `pt` (points), and `px` (pixels).
- **Output**: SVG.

## Configuration Reference

### Common Properties
All elements (groups and components) support these properties:
- `id`: Unique identifier (string).
- `type`: Element type (`group`, `potentiometer`, `socket`, `switch`).
- `x`, `y`: Position relative to the parent group (or panel origin). Supports units (e.g., `"20mm"`, `"1in"`).
- `label`: Text label (string).
- `label_position`: Position of the label (see below).
- `font`: Font styling (see below).

### Panel
Top-level configuration.
- `name`: Panel name.
- `width`, `height`: Panel dimensions.
- `background_color`: Hex color string (e.g., `"#dddddd"`).
- `elements`: List of root elements.

### Components

#### Group
A container for other elements.
- `width`, `height`: Dimensions of the group area.
- `border`: Border styling (see below).
- `elements`: List of child elements.
- `label_position`:
    - `top-outside` (default), `bottom-outside`
    - `top-inline`, `bottom-inline`: Centered on the border line (interrupts border).
    - `top-inside`, `bottom-inside`: Inside the border.

#### Potentiometer
- `radius`: Radius of the knob/body (default: `15mm`).
- `scale`: Scale markings (e.g., `0-10`, currently simplified).
- `label_position`: `top`, `bottom` (default).

#### Socket
- `radius`: Radius of the socket (default: `10mm`).
- `label_position`: `top`, `bottom` (default).

#### Switch
- `width`: Switch body width (default: `10mm`).
- `height`: Switch body height (default: `20mm`).
- `label_position`: `top`, `bottom` (default).

### Styling Options

#### Border
Applies to Groups.
```yaml
border:
  type: "full"      # Options: "none", "full", "top", "bottom"
  thickness: "1mm"  # Line thickness
  style: "dotted"   # Options: "full" (solid), "dotted", "dashed"
  color: "black"    # Hex color or name
```

#### Font
Applies to any element.
```yaml
font:
  size: "12pt"      # Font size
  color: "blue"     # Text color
  family: "serif"   # Font family (e.g., "sans-serif", "serif", "monospace")
  weight: "bold"    # Options: "normal", "bold"
```

### Label Positioning
- **Components**: `top`, `bottom`.
- **Groups**: `top-outside`, `bottom-outside`, `top-inline`, `bottom-inline`, `top-inside`, `bottom-inside`.

### Units
If no unit is specified, `mm` is assumed.
- `mm` (millimeters)
- `cm` (centimeters)
- `in` or `"` (inches)
- `pt` (points)
- `px` (pixels)

## Example

```yaml
name: "My Amp Panel"
width: "45cm"
height: "150mm"
background_color: "#dddddd"

elements:
  - type: group
    label: "PREAMP"
    label_position: "top-inline"
    x: "20mm"
    y: "20mm"
    width: "140mm"
    height: "100mm"
    border:
      type: "full"
      style: "full"
      thickness: "2mm"
    elements:
      - type: potentiometer
        label: "VOLUME"
        x: "30mm"
        y: "40mm"
        font:
          weight: "bold"
```
