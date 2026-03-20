import argparse
import yaml
import sys
import traceback
from pathlib import Path
from models import Panel, set_dpi
from renderer import PanelRenderer

def main():
    parser = argparse.ArgumentParser(description="Generate instrument panel SVG from YAML.")
    parser.add_argument("--dpi", type=float, default=96.0, help="DPI used for converting `px` units to millimeters (default: 96).")
    parser.add_argument("input_file", help="Path to the input YAML file")
    parser.add_argument("output_file", help="Path to the output SVG file")
    
    args = parser.parse_args()
    
    try:
        set_dpi(args.dpi)
        with open(args.input_file, 'r') as f:
            data = yaml.safe_load(f)
        
        panel = Panel.from_dict(data)

        base_dir = str(Path(args.input_file).resolve().parent)
        renderer = PanelRenderer(panel, base_dir=base_dir)
        renderer.render(args.output_file)
        
        print(f"Successfully generated {args.output_file}")
        
    except FileNotFoundError:
        print(f"Error: Could not find file {args.input_file}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        sys.exit(1)
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
