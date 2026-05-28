"""Evaluation utilities: compute statistics and plots for a schedule."""
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import csv
import json
import math
from typing import List, Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from domain.cadet import Cadet
from domain.job import Shift
from scheduling.schedule import Schedule


@dataclass
class CadetStats:
    personal_number: str
    name: str
    assigned_count: int
    total_hours: float
    avg_difficulty: float
    workload_score: float


class Evaluator:
    """Create statistics and plots from a Schedule.

    Outputs a folder with CSV/JSON summaries and PNG plots.
    """

    def evaluate(self, schedule: Schedule, cadets: List[Cadet], output_path: str) -> None:
        out = Path(output_path)
        if out.suffix == ".xlsx":
            out = out.with_suffix("")
        # evaluation folder inside output base
        eval_dir = out / "evaluation"
        eval_dir.mkdir(parents=True, exist_ok=True)

        # compute per-cadet assigned shifts
        assigned: Dict[str, List[Shift]] = defaultdict(list)
        for s in schedule.assignments:
            if s.assigned_cadet:
                assigned[s.assigned_cadet.personal_number].append(s)

        cadet_map = {c.personal_number: c for c in cadets}

        stats: List[CadetStats] = []
        difficulties = []
        hours = []

        for pn, cadet in cadet_map.items():
            shifts = assigned.get(pn, [])
            assigned_count = len(shifts)
            total_hours = sum(s.duration_hours for s in shifts)
            avg_diff = float(sum(s.difficulty for s in shifts) / assigned_count) if assigned_count else 0.0
            # geometric mean
            geom = 0.0
            if assigned_count:
                prod = 1.0
                for s in shifts:
                    prod *= s.difficulty
                geom = prod ** (1.0 / assigned_count)
            workload_score = geom * total_hours

            stats.append(CadetStats(
                personal_number=pn,
                name=cadet.name,
                assigned_count=assigned_count,
                total_hours=total_hours,
                avg_difficulty=avg_diff,
                workload_score=workload_score,
            ))

            # collect global lists
            for s in shifts:
                difficulties.append(s.difficulty)
            hours.append(total_hours)

        # write per-cadet CSV
        csv_path = eval_dir / "cadet_stats.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["personal_number", "name", "assigned_count", "total_hours", "avg_difficulty", "workload_score"])
            for c in sorted(stats, key=lambda x: x.personal_number):
                writer.writerow([c.personal_number, c.name, c.assigned_count, f"{c.total_hours:.2f}", f"{c.avg_difficulty:.3f}", f"{c.workload_score:.3f}"])

        # write JSON summary
        # compute mean workload across cadets
        workload_scores = [c.workload_score for c in stats]
        mean_workload = float(sum(workload_scores) / len(workload_scores)) if workload_scores else 0.0

        summary = {
            "num_cadets": len(cadet_map),
            "num_assigned_shifts": sum(s.assigned_cadet is not None for s in schedule.assignments),
            "total_shifts": len(schedule.assignments),
            "difficulty_mean": float(sum(difficulties) / len(difficulties)) if difficulties else 0.0,
            "difficulty_median": float(sorted(difficulties)[len(difficulties)//2]) if difficulties else 0.0,
            "mean_workload": mean_workload,
        }
        with open(eval_dir / "summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        # Plot: histogram of shift difficulties
        if difficulties:
            plt.figure(figsize=(6,4))
            plt.hist(difficulties, bins=range(1,12), align='left', edgecolor='black')
            plt.title('Shift Difficulty Distribution')
            plt.xlabel('Difficulty')
            plt.ylabel('Count')
            plt.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            plt.savefig(eval_dir / 'difficulty_histogram.png')
            plt.close()

        # Plot: histogram of total hours per cadet
        plt.figure(figsize=(6,4))
        plt.hist(hours, bins=10, edgecolor='black')
        plt.title('Assigned Hours per Cadet')
        plt.xlabel('Hours')
        plt.ylabel('Number of Cadets')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        plt.savefig(eval_dir / 'hours_histogram.png')
        plt.close()

        # Plot: workload score distribution
        scores = [c.workload_score for c in stats]
        plt.figure(figsize=(6,4))
        plt.hist(scores, bins=10, edgecolor='black')
        plt.title('Workload Score Distribution')
        plt.xlabel('Workload Score')
        plt.ylabel('Number of Cadets')
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        plt.savefig(eval_dir / 'workload_histogram.png')
        plt.close()

        # Scatter: hours vs workload
        plt.figure(figsize=(6,4))
        plt.scatter(hours, scores)
        plt.title('Total Hours vs Workload Score')
        plt.xlabel('Total Hours')
        plt.ylabel('Workload Score')
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(eval_dir / 'hours_vs_workload.png')
        plt.close()
