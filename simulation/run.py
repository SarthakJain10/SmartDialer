import argparse
import asyncio
from simulation.scenarios import run_simulation_engine


async def compare_modes():
    print("Running Comparative Analysis (Progressive vs Predictive)...")
    prog_metrics = await run_simulation_engine(mode="progressive", provider_type="A", duration=5.0)
    pred_metrics = await run_simulation_engine(mode="predictive", provider_type="A", duration=5.0)

    prog_metrics.print_summary()
    pred_metrics.print_summary()


def main():
    parser = argparse.ArgumentParser(description="SmartDialer Simulator CLI")
    parser.add_argument("--mode", choices=["progressive", "predictive", "compare"], default="predictive")
    parser.add_argument("--provider", choices=["A", "B"], default="A")
    parser.add_argument("--agents", type=int, default=20)
    parser.add_argument("--borrowers", type=int, default=100)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    if args.mode == "compare":
        asyncio.run(compare_modes())
    else:
        metrics = asyncio.run(
            run_simulation_engine(
                mode=args.mode,
                provider_type=args.provider,
                agents_count=args.agents,
                borrowers_count=args.borrowers,
                duration=args.duration,
                seed=args.seed,
            )
        )
        metrics.print_summary()


if __name__ == "__main__":
    main()