import sys
import os

# Add the 'core' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'core')))

from core.sara import SaraAgent

if __name__ == "__main__":
    try:
        agent = SaraAgent()
        agent.console.print("[bold green]SARA Initialized Successfully from main.py[/]")
        agent.sara_completer  # Just touching it to ensure it loaded
        # Start SARA CLI
        agent.run() 
    except KeyboardInterrupt:
        print("\nExiting SARA...")
    except Exception as e:
        print(f"Error initializing SARA: {e}")
