# Panel Maker

A tool to design instrument amplifier panels declaratively using YAML.

## Usage

1. Define your panel in a YAML file (e.g., `panel.yaml`).
2. Run the generator: `python main.py panel.yaml output.svg`.

## Features

- **Components**: Potentiometers, Switches, Sockets, Custom components.
- **Grouping**: Recursive groups with relative positioning.
- **Styling**: Customizable borders, fonts, and label positioning.
- **Units**: Support for `mm` (default), `cm`, `in` (inches), `pt` (points), and `px` (pixels).
- **Output**: SVG.

## Configuration Reference

### Panel
Top-level configuration.
- `name`: Panel name.
- `width`, `height`: Panel dimensions.
- `background_color`: Hex color string (e.g., `"#dddddd"`).
- `render_mode`: Controls component visualization. Options:
    - `"show"`: Render components fully.
    - `"hide"`: Render drill patterns only (crosshairs + hole).
    - `"both"` (default): Render components with drill patterns underneath (components are semi-transparent).
- `elements`: List of root elements.

### Common Properties
All elements (groups and components) support these properties:
- `id`: Unique identifier (string).
- `type`: Element type (`group`, `potentiometer`, `socket`, `switch`, `custom`).
- `x`, `y`: Position relative to the parent group (or panel origin). Supports units (e.g., `"20mm"`, `"1in"`).
- `label`: Configuration for the main label.
    - `text`: The label text (string).
    - `position`: Position of the label (see Label Positioning below).
    - `distance`: Custom distance from the component center (optional).
    - `font`: Font styling (see Font below). This font applies to the label and is used as the default for other text on the component (e.g., scales).

### Components

#### Group
A container for other elements.
- `width`, `height`: Dimensions of the group area.
- `border`: Border styling (see below).
- `elements`: List of child elements.

#### Potentiometer
- `knob_diameter`: Diameter of the knob (default: `20mm`).
- `border_diameter`: Diameter of the surrounding border/scale ring (default: `25mm`).
- `border_thickness`: Thickness of the ring (default: `0`, no border).
- `scale`: Scale configuration (see below).
- `mount`: Mounting hole configuration (see below). Default diameter: `6mm`.

#### Socket
- `radius`: Radius of the socket body (default: `10mm`).
- `mount`: Mounting hole configuration (see below). Default diameter: `10mm`.

#### Switch
- `switch_type`: `"toggle"` (default) or `"rotary"`.
- `width`, `height`: Body dimensions (for toggle).
- `knob_diameter`: Knob diameter (for rotary).
- `mount`: Mounting hole configuration (see below). Default diameter: `5mm`.

**Toggle Switch Specifics:**
- `label_top`: Text label above the switch. Can be a string or a Label object.
- `label_bottom`: Text label below the switch. Can be a string or a Label object.
- `label_center`: Text label to the right/center. Can be a string or a Label object.

**Rotary Switch Specifics:**
- `scale`: Scale configuration (see below).
- `angle_start`: Starting angle in degrees (default: 45).
- `angle_width`: Total sweep angle in degrees (default: 270).

#### Custom
A generic component defined by its mounting hole.
- `mount`: Mounting hole configuration (see below). Required for visualization.
- `label`: Component label.

When rendered (in `show` or `both` mode), it displays a generic shape (circle or rectangle) matching the mounting dimensions.

### Styling and Configuration

#### Scale Configuration
Applies to Potentiometers and Rotary Switches.
- `num_ticks`: Total number of ticks.
- `major_tick_interval`: Interval for major (longer) ticks.
- `tick_style`: `"line"` or `"dot"`.
- `tick_size`: Length/size of major ticks (minor are half).
- `labels`: List of labels for ticks (mainly for Rotary Switches). Items can be strings or Label objects.

```yaml
scale:
  num_ticks: 3
  tick_size: "4mm"
  labels:
    - text: "4"
      font: { color: "red" }
    - "8"
    - "16"
```

#### Mount Configuration
Defines the drill hole pattern. You must specify either `diameter` (for circular holes) OR both `width` and `height` (for rectangular holes).

```yaml
mount:
  diameter: "10mm"  # Circular hole
```
OR
```yaml
mount:
  width: "6mm"      # Rectangular hole
  height: "12mm"
```

#### Label Configuration
This structure is used for the main `label` parameter, toggle labels (`label_top` etc.), and items in `scale.labels`.
```yaml
label:
  text: "VOLUME"
  position: "bottom"
  distance: "20mm"  # Optional distance from component center
  font:
    size: "12pt"
    color: "black"
    family: "serif"
    weight: "bold"
```
*Note: `position` is applicable for the main component label. `distance` overrides automatic placement calculations.*

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
Defined within the `label` block.
- `size`: Font size (e.g. "12pt", "4mm").
- `color`: Text color.
- `family`: Font family.
- `weight`: Font weight.

### Label Positioning
- **Components**: `top`, `bottom`.
- **Groups**: `top-outside` (default), `bottom-outside`, `top-inline`, `bottom-inline`, `top-inside`, `bottom-inside`.
- **Inline**: For groups, `*-inline` positions center the label on the border line and interrupt the border.

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
render_mode: "both"

elements:
  - type: custom
    id: "fuse"
    x: "20mm"
    y: "20mm"
    mount:
      diameter: "12mm"
    label:
      text: "FUSE"
      position: "bottom"
      distance: "15mm"
```
