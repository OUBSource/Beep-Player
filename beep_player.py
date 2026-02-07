import ctypes
import time
import os
import sys
import argparse

# --- Configuration ---
DEFAULT_DURATION = 0.3  # Seconds per note
DEFAULT_GAP = 0.05      # Silence between notes

# --- Note Frequencies (Octave 3-5) ---
NOTES_FREQ = {
    'C3': 130.81, 'C#3': 138.59, 'D3': 146.83, 'D#3': 155.56, 'E3': 164.81, 'F3': 174.61, 'F#3': 185.00, 'G3': 196.00, 'G#3': 207.65, 'A3': 220.00, 'A#3': 233.08, 'B3': 246.94,
    'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13, 'E4': 329.63, 'F4': 349.23, 'F#4': 369.99, 'G4': 392.00, 'G#4': 415.30, 'A4': 440.00, 'A#4': 466.16, 'B4': 493.88,
    'C5': 523.25, 'C#5': 554.37, 'D5': 587.33, 'D#5': 622.25, 'E5': 659.25, 'F5': 698.46, 'F#5': 739.99, 'G5': 783.99, 'G#5': 830.61, 'A5': 880.00, 'A#5': 932.33, 'B5': 987.77
}

def get_inpout_driver():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    is_64bit_python = sys.maxsize > 2**32
    dll_name = "InpOutx64.dll" if is_64bit_python else "InpOut32.dll"
    dll_path = os.path.join(script_dir, dll_name)

    if not os.path.exists(dll_path):
        print(f"ERROR: {dll_name} not found in: {script_dir}")
        sys.exit(1)

    try:
        driver = ctypes.windll.LoadLibrary(dll_path)
        return driver, is_64bit_python
    except OSError as e:
        print(f"ERROR loading DLL: {e}")
        print("Ensure Visual C++ Redistributable is installed and the DLL is not blocked.")
        sys.exit(1)

# Initialize Driver
inpout, is_64bit = get_inpout_driver()

def out_port(port, data):
    if is_64bit:
        inpout.DlPortWritePortUchar(port, data)
    else:
        inpout.Out32(port, data)

def in_port(port):
    if is_64bit:
        return inpout.DlPortReadPortUchar(port)
    else:
        return inpout.Inp32(port)

def hardware_beep(freq, duration):
    freq = int(freq)
    if freq < 37 or freq > 32767:
        return # Ignore invalid frequencies

    divisor = int(1193180 / freq)

    # Setup PIT 8254
    out_port(0x43, 0xB6)
    out_port(0x42, divisor & 0xFF)
    out_port(0x42, (divisor >> 8) & 0xFF)

    # Enable Speaker (Bits 0 and 1 of port 0x61)
    val = in_port(0x61)
    out_port(0x61, val | 0x03)

    time.sleep(duration)

    # Disable Speaker
    val = in_port(0x61)
    out_port(0x61, val & 0xFC)

def parse_and_play(notes_str):
    """Parses a string of notes and plays them."""
    tokens = notes_str.replace(",", " ").split()
    
    for token in tokens:
        freq = 0
        token = token.upper()
        
        if token in NOTES_FREQ:
            freq = NOTES_FREQ[token]
        elif token.isdigit():
            freq = int(token)
        
        if freq > 0:
            hardware_beep(freq, DEFAULT_DURATION)
            time.sleep(DEFAULT_GAP)
        else:
            # If it's not a note/number (like "P" or "-"), treat as pause
            time.sleep(DEFAULT_DURATION)

def is_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def interactive_mode():
    print("\n--- PC Speaker Player ---")
    print("Enter notes separated by space (e.g., 'C4 E4 G4' or '440 880').")
    print("Type 'exit' to quit.\n")
    
    while True:
        try:
            user_input = input(">> ")
            if user_input.lower() in ['exit', 'quit']:
                break
            parse_and_play(user_input)
        except KeyboardInterrupt:
            print("\nExiting...")
            break

def main():
    if not is_admin():
        print("ERROR: Administrator privileges required to access hardware ports.")
        print("Please run as Administrator.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="PC Speaker CLI Player")
    parser.add_argument("--notes", type=str, help="Notes string (e.g. 'C4 E4 G4')")
    parser.add_argument("--loop", type=str, choices=['true', 'false'], default='false', help="Loop playback")
    
    args = parser.parse_args()

    if args.notes:
        # CLI Mode
        should_loop = args.loop.lower() == 'true'
        try:
            if should_loop:
                print(f"Playing loop (Press Ctrl+C to stop)...")
                while True:
                    parse_and_play(args.notes)
                    time.sleep(0.5) # Pause between loops
            else:
                parse_and_play(args.notes)
        except KeyboardInterrupt:
            sys.exit(0)
    else:
        # Interactive Mode (No arguments provided)
        interactive_mode()

if __name__ == "__main__":
    main()