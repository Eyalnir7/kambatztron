"""CLI entrypoint for the shift scheduler."""
import argparse
from app import ShiftSchedulerApp


def main():
    parser = argparse.ArgumentParser(description="Shift Scheduler CLI")
    parser.add_argument("--cadets", required=True)
    parser.add_argument("--jobs", required=True)
    parser.add_argument("--constraints", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    app = ShiftSchedulerApp()
    app.run(args.cadets, args.jobs, args.constraints, args.output)


if __name__ == "__main__":
    main()
