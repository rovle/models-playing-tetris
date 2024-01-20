from dataclasses import dataclass, field
from typing import List, Optional, Callable
import json
import os
import math
from collections import defaultdict

all_jsons = []
for game_folder in os.listdir("games_archive"):
    info_path = f"games_archive/{game_folder}/info.json"
    try:
        with open(info_path, "r") as fp:
            info = json.load(fp)
        all_jsons.append(info)
    except FileNotFoundError:
        continue


@dataclass
class TetrisData:
    model: str
    pieces_count: int
    temperature: Optional[float] = None
    tetris_seed: Optional[int] = None
    prompt_name: Optional[str] = None
    example_ids: List = field(default_factory=list)
    lines_cleared: int = 0
    score: int = 0
    n_lines: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    t_spins: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    combo: int = 0

    @staticmethod
    def group_by_fields(records: List['TetrisData'], fields: List[str]) -> dict:
        grouped_records = defaultdict(list)
        for record in records:
            # Convert list fields to tuples for hashing
            key = tuple(getattr(record, field) if not isinstance(getattr(record, field), list) else tuple(getattr(record, field)) for field in fields)
            grouped_records[key].append(record)
        return grouped_records
    @staticmethod
    def filter_records(
        records: List['TetrisData'],
        condition: Callable[['TetrisData'], bool]
                       ) -> List['TetrisData']:
        return [record for record in records if condition(record)]

    @staticmethod
    def average_pieces_count(records: List['TetrisData']) -> float:
        average = sum(record.pieces_count for record in records) / len(records) if records else 0
        return round(average, 2)
    
    def average_lines_cleared(records: List['TetrisData']) -> float:
        average = sum(record.lines_cleared for record in records) / len(records) if records else 0
        return average

    @staticmethod
    def confidence_interval_95(records: List['TetrisData'],
                               attribute: str) -> Optional[tuple]:
        if not records or attribute not in vars(records[0]):
            return None

        n = len(records)
        mean = sum(getattr(record, attribute) for record in records) / n
        std_dev = (sum((getattr(record, attribute) - mean) ** 2 for record in records) / n) ** 0.5
        sem = std_dev / math.sqrt(n)
        z_score = 1.96  # Z-score for 95% confidence
        margin_of_error = z_score * sem

        lower_bound = mean - margin_of_error
        upper_bound = mean + margin_of_error

        return round(lower_bound, 2), round(upper_bound, 2)


import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--model", type=str)
parser.add_argument("--temperature", type=float)
parser.add_argument("--prompt_name", type=str)
parser.add_argument("--example_ids", nargs="*", type=int, help="-1 to specify games without examples")
parser.add_argument("--tetris_seed", type=int)
args = parser.parse_args()

tetris_records = [TetrisData(**item) for item in all_jsons]

def model_filter(record):
    # for each argument, check if it satisfies the condition
    if args.model and record.model != args.model:
        return False
    if args.temperature and record.temperature != args.temperature:
        return False
    if args.prompt_name and record.prompt_name != args.prompt_name:
        return False
    if args.example_ids == []:
        if record.example_ids:
            return False
    elif args.example_ids is not None and record.example_ids != args.example_ids:
        return False
    if args.tetris_seed and record.tetris_seed != args.tetris_seed:
        return False
    return True

if __name__ == "__main__":
    if args.example_ids == [-1]:
        args.example_ids = []
    filtered_records = TetrisData.filter_records(tetris_records, model_filter)

    print("Data for records with the following parameters:")
    # check if each argument is not None, and print it
    if args.model:
        print(f"Model: {args.model}")
    if args.temperature:
        print(f"Temperature: {args.temperature}")
    if args.prompt_name:
        print(f"Prompt Name: {args.prompt_name}")
    if args.example_ids or args.example_ids == []:
        print(f"Example IDs: {args.example_ids}")
    if args.tetris_seed:
        print(f"Tetris Seed: {args.tetris_seed}")

    avg_lines_cleared = TetrisData.average_lines_cleared(filtered_records)
    print(f"Average Lines Cleared: {avg_lines_cleared}")

    avg_pieces_count = TetrisData.average_pieces_count(filtered_records)
    print(f"Average Pieces Count: {avg_pieces_count}")

    ci_pieces_count = TetrisData.confidence_interval_95(filtered_records, 'pieces_count')
    print(f"95% Confidence Interval for Pieces Count: {ci_pieces_count}")
    print(f"Number of Games: {len(filtered_records)}")
    print("\n---\n")
    # group by each argument that is None, and print the average pieces count for each group
    unspecified_fields = [field
                          for field in ['model', 'temperature', 'prompt_name',
                                        'example_ids', 'tetris_seed']
                          if not getattr(args, field)]
    grouped_records = TetrisData.group_by_fields(filtered_records, unspecified_fields)

    average_scores_by_group = {key: (TetrisData.average_pieces_count(group), len(group))
                               for key, group in grouped_records.items()}

    # Sort the groups by average score in descending order
    sorted_average_scores = sorted(average_scores_by_group.items(), key=lambda x: x[1], reverse=True)

    for key, (avg_score, count) in sorted_average_scores:
        labeled_key = ", ".join(f"{field}: {value}" for field, value in zip(unspecified_fields, key))
        print(f"Group ({labeled_key}): Average Score = {avg_score}, Number of Games = {count}")
