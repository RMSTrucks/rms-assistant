"""
RMS Agent - Main Entry Point

AI assistant for RMS Trucks insurance agency.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from app.agent import get_agent, run_agent


def interactive_mode():
    """Run the agent in interactive CLI mode."""
    print("RMS Insurance Assistant")
    print("=" * 50)
    print("I can help with DOT lookups, CRM tasks, policy info, and more.")
    print("Type 'quit' or 'exit' to end the session.\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            response = run_agent(user_input)
            print(f"\nAssistant: {response}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def single_task(task: str):
    """Run a single task and exit."""
    response = run_agent(task)
    print(response)


def main():
    """Main entry point."""
    # Check for required environment variables
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is required")
        sys.exit(1)

    # Check command line arguments
    if len(sys.argv) > 1:
        # Join all arguments as a single task
        task = " ".join(sys.argv[1:])
        single_task(task)
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
