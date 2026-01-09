import time
import os
import sys

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def type_writer(text, speed=0.03):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)
    print()

def run_tutorial(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by step delimiter
    steps = content.split('---STEP---')

    clear_screen()
    print("🚀 HYPERCODE INTERACTIVE TUTORIAL")
    print("=================================")
    
    for i, step in enumerate(steps):
        step = step.strip()
        if not step:
            continue

        lines = step.split('\n')
        
        # Extract metadata if any (simple parsing)
        instruction = []
        code_block = []
        in_code = False

        for line in lines:
            if line.startswith("```"):
                in_code = not in_code
                continue
            
            if in_code:
                code_block.append(line)
            else:
                instruction.append(line)

        # Display Instruction
        print(f"\n📝 Step {i+1}:")
        type_writer("\n".join(instruction))

        if code_block:
            print("\n💻 Code to Execute:")
            print("-------------------")
            for line in code_block:
                print(f"  {line}")
            print("-------------------")
        
        input("\n[Press Enter to Continue...]")
        
        # Simulate "Running"
        if code_block:
            print("⚙️ Running HyperCode VM...")
            time.sleep(1)
            print("✅ Success! Output captured.\n")
            time.sleep(0.5)

    print("\n🎉 Tutorial Complete! You are now a HyperCode Novice.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tutorial_runner.py <tutorial.hc>")
        sys.exit(1)
    
    run_tutorial(sys.argv[1])
