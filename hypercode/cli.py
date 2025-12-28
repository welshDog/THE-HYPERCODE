"""HyperCode CLI (command-line interface)."""

import argparse
import sys


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="HyperCode: Programming language for neurodivergent brains"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # parse command
    parse_parser = subparsers.add_parser("parse", help="Parse HyperCode file")
    parse_parser.add_argument("file", help="Input .hc file")
    
    # ir command
    ir_parser = subparsers.add_parser("ir", help="Generate IR from HyperCode file")
    ir_parser.add_argument("file", help="Input .hc file")
    
    # run command
    run_parser = subparsers.add_parser("run", help="Run HyperCode program")
    run_parser.add_argument("file", help="Input .hc file")
    run_parser.add_argument(
        "--backend",
        choices=["qiskit", "classical", "molecular"],
        default="qiskit",
        help="Backend to use"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "parse":
        print(f"Parsing {args.file}...")
        # TODO: Implement parsing
    elif args.command == "ir":
        print(f"Generating IR for {args.file}...")
        # TODO: Implement IR generation
    elif args.command == "run":
        print(f"Running {args.file} with {args.backend} backend...")
        # TODO: Implement execution


if __name__ == "__main__":
    main()
