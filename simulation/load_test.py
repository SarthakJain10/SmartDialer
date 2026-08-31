import asyncio
import time
from simulation.scenarios import run_simulation_engine


async def main():
    print("Starting SmartDialer Load Test (100 Agents, 1000 Borrowers)...")
    start = time.time()
    metrics = await run_simulation_engine(
        mode="predictive",
        provider_type="A",
        agents_count=100,
        borrowers_count=1000,
        duration=3.0,
    )
    elapsed = time.time() - start

    metrics.print_summary()
    print(f"Load Test Completed in {elapsed:.2f} seconds.")


if __name__ == "__main__":
    asyncio.run(main())