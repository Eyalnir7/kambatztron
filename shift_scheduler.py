"""CLI entrypoint for the shift scheduler."""
import argparse
from app import ShiftSchedulerApp


def main():
    parser = argparse.ArgumentParser(description="Shift Scheduler CLI")
    parser.add_argument("--cadets", required=True)
    parser.add_argument("--jobs", required=True)
    parser.add_argument("--constraints", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--t-rest", type=float, default=8.0, help="Minimum rest gap in hours (default: 8)")
    parser.add_argument("--rho", type=float, default=2.0, help="Penalty weight rho (default: 2.0)")

    args = parser.parse_args()

    app = ShiftSchedulerApp()
    app.run(args.cadets, args.jobs, args.constraints, args.output, T_rest=args.t_rest, rho=args.rho)


if __name__ == "__main__":
    main()
