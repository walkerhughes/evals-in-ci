"""Run a Harbor evaluation job in a Modal sandbox and write results locally."""

import asyncio
import json
import sys
from pathlib import Path

from harbor import Job, JobConfig, TaskConfig, AgentConfig, ArtifactConfig
from harbor.models.environment import EnvironmentConfig
from harbor.models.environment_type import EnvironmentType


async def run() -> Path:
    config = JobConfig(
        job_name="ci-eval",
        jobs_dir=Path("./jobs"),
        tasks=[
            TaskConfig(path=Path("./tasks/hello-world")),
        ],
        # -- agent --------------------------------------------------------
        agents=[
            AgentConfig(
                # TODO: set the agent you want to evaluate
                name="claude-code",
            ),
        ],
        # -- environment (Modal) -----------------------------------------
        environment=EnvironmentConfig(
            type=EnvironmentType.MODAL,
            # Adjust resources as needed:
            # override_cpus=4,
            # override_memory_mb=8192,
        ),
        # -- artifacts to collect from the sandbox -----------------------
        artifacts=[
            "/logs/artifacts",  # Harbor convention directory
        ],
        # -- execution params --------------------------------------------
        n_attempts=1,
        n_concurrent_trials=1,
    )

    job = await Job.create(config)
    result = await job.run()

    # Print a summary to stdout for CI logs
    print(f"Job completed: {result.n_total_trials} trial(s), "
          f"{result.stats.n_errors} error(s)")

    # Write the result summary as a standalone JSON file for easy consumption
    summary_path = job.job_dir / "summary.json"
    summary_path.write_text(json.dumps({
        "job_id": str(result.id),
        "n_total_trials": result.n_total_trials,
        "n_errors": result.stats.n_errors,
        "started_at": str(result.started_at),
        "finished_at": str(result.finished_at),
        "trial_results": [
            {
                "trial_name": t.trial_name,
                "task_name": t.task_name,
                "rewards": (
                    t.verifier_result.rewards
                    if t.verifier_result else None
                ),
            }
            for t in result.trial_results
        ],
    }, indent=2))

    return job.job_dir


def main() -> None:
    job_dir = asyncio.run(run())
    print(f"::set-output name=job_dir::{job_dir}")
    # Also write to GITHUB_OUTPUT if available
    import os
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"job_dir={job_dir}\n")


if __name__ == "__main__":
    main()
