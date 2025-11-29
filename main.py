import argparse
import yaml
import sys
import traceback
from models import Panel
from renderer import PanelRenderer

def main():
    parser = argparse.ArgumentParser(description="Generate instrument panel SVG from YAML.")
    parser.add_argument("input_file", help="Path to the input YAML file")
    parser.add_argument("output_file", help="Path to the output SVG file")
    
    args = parser.parse_args()
    
    try:
        with open(args.input_file, 'r') as f:
            data = yaml.safe_load(f)
        
        panel = Panel.from_dict(data)
        
        renderer = PanelRenderer(panel)
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
