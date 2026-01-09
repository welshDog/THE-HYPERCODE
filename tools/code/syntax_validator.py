import sys
import re

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def validate_file(filepath):
    print(f"{Colors.HEADER}🔍 Scanning: {filepath}{Colors.ENDC}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    errors = 0
    warnings = 0

    # Rule 1: Check for Domain Header
    has_domain = False
    for line in lines[:5]:  # Check first 5 lines
        if line.strip().startswith("#:domain"):
            has_domain = True
            break
    
    if not has_domain:
        print(f"{Colors.FAIL}[Error] Missing #:domain directive at top of file.{Colors.ENDC}")
        errors += 1

    # Line-by-line checks
    for i, line in enumerate(lines):
        line_num = i + 1
        stripped = line.strip()
        
        if not stripped or stripped.startswith("#"):
            continue

        # Rule 2: Legacy Keyword Detection
        legacy_keywords = ["function ", "circuit ", "if ", "else:", "for "]
        for kw in legacy_keywords:
            if stripped.startswith(kw):
                print(f"{Colors.FAIL}[Error] Line {line_num}: Found legacy keyword '{kw.strip()}'. Use '@{kw.strip()}' instead.{Colors.ENDC}")
                print(f"    {stripped}")
                errors += 1

        # Rule 3: Register Types
        if "QuantumRegister" in stripped:
             print(f"{Colors.WARNING}[Warning] Line {line_num}: Verbose 'QuantumRegister' found. Recommend 'QReg'.{Colors.ENDC}")
             warnings += 1

        # Rule 4: Gate Syntax
        # Simple regex for Capital Letter Gates like "H q0" (start of line)
        if re.match(r'^[A-Z]{1,3}\s+', stripped):
             # Exclude some false positives if possible, but this catches H, CX, X
             print(f"{Colors.FAIL}[Error] Line {line_num}: Legacy gate syntax detected. Use decorators (e.g., '@hadamard').{Colors.ENDC}")
             print(f"    {stripped}")
             errors += 1

    # Summary
    if errors == 0:
        print(f"{Colors.OKGREEN}✅ Syntax Validated. {warnings} Warnings.{Colors.ENDC}")
        return True
    else:
        print(f"{Colors.FAIL}❌ Validation Failed. {errors} Errors, {warnings} Warnings.{Colors.ENDC}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python syntax_validator.py <file.hc>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    validate_file(filepath)
