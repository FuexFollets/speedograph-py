from __future__ import annotations

import json
import time
from typing import overload
import aiohttp
import os
import parse
from dataclasses import dataclass
from pprint import pprint

from speedograph.constants import (
    CACHE_DATA_PATH,
    FILENAME_FORMAT,
    API_URL,
    TYPERACER_START_EPOCH,
    COLLECTION_WINDOW_EPOCH,
)

"""
Sample
  {
    "wpm": 100.39,
    "ac": 0.98,
    "r": 3,
    "t": 1689255748.324,
    "sl": "L6",
    "tid": 4350102,
    "gn": 2319,
    "np": 3,
    "pts": 150.59
  }
"""


@dataclass
class Race:
    words_per_minute: float
    accuracy: float
    rank: int
    epoch_timestamp: float
    speedometer_level: str
    text_id: int
    game_number: int
    number_of_players: int
    points: float

    @classmethod
    def from_json_content(cls, json_content):
        return cls(
                json_content["wpm"],
                json_content["ac"],
                json_content["r"],
                json_content["t"],
                json_content["sl"],
                json_content["tid"],
                json_content["gn"],
                json_content["np"],
                json_content["pts"],
            )

@dataclass
class EpochInterval:
    start: int
    end: int

    @overload
    def contains(self, epoch: EpochInterval) -> bool:
        ...

    @overload
    def contains(self, epoch: int) -> bool:
        ...

    def contains(self, epoch: int | EpochInterval) -> bool:
        if isinstance(epoch, EpochInterval):
            return self.start <= epoch.start and epoch.end <= self.end

        return self.start <= epoch <= self.end

    def interval_length(self) -> int:
        return self.end - self.start + 1

    def divide_into(self, number_of_parts: int) -> list[EpochInterval]:
        if number_of_parts < 1:
            number_of_parts = 1

        if number_of_parts == 1:
            return [self]

        interval_length_per_part: int = self.interval_length() // number_of_parts
        intervals: list[EpochInterval] = []

        for iteration in range(number_of_parts):
            intervals.append(
                EpochInterval(
                    self.start + iteration * interval_length_per_part,
                    self.start + (iteration + 1) * interval_length_per_part - 1,
                )
            )

        return intervals

    def minimum_divisions(self, maximum_interval_length: int) -> int:
        return self.interval_length() // maximum_interval_length

    def __eq__(self, other: EpochInterval) -> bool:
        return self.start == other.start and self.end == other.end

class Collection:
    def __init__(self, username: str):
        self.username: str = username
        self.data_samples: list[Race] = []
        self._precollected_epoch_intervals: list[EpochInterval] = []
        self.cache_path = CACHE_DATA_PATH.format(username=self.username)

    def ensure_path(self) -> Collection:
        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

        return self

    async def call_api(self, interval: EpochInterval) -> str:
        url: str = API_URL.format(
            username=self.username,
            start_epoch=interval.start,
            end_epoch=interval.end,
        )

        print("calling api for interval", interval.start, interval.end)

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()

    async def collect(self, cache_data: bool = False) -> Collection:
        self.load_from_cache()
        print("precollected_epoch_intervals", self._precollected_epoch_intervals)

        current_epoch: int = int(time.time())
        responses: list[str] = []
        uncollected_intervals: list[EpochInterval] = []
        divided_uncollected_intervals: list[EpochInterval] = []

        last_epoch_begin: int = TYPERACER_START_EPOCH

        for interval in self._precollected_epoch_intervals:
            uncollected_intervals.append(
                EpochInterval(last_epoch_begin, interval.start - 1)
            )
            last_epoch_begin = interval.end + 1

        uncollected_intervals.append(
            EpochInterval(last_epoch_begin, current_epoch)
        )

        for interval in uncollected_intervals:
            divided_uncollected_intervals += interval.divide_into(
                interval.minimum_divisions(COLLECTION_WINDOW_EPOCH)
            )

        print("divided_uncollected_intervals", divided_uncollected_intervals)

        for interval in divided_uncollected_intervals:
            json_response: str = await self.call_api(interval)
            responses.append(json_response)

            print(f"json_response: {json_response}")

            if cache_data:
                try:
                    self.cache_file(interval, json.loads(json_response))
                except json.JSONDecodeError:
                    self.cache_file(interval, {})

        return self

    def cache_file(self, interval: EpochInterval, json_content: dict):
        filename: str = FILENAME_FORMAT.format(
            start_epoch=interval.start,
            end_epoch=interval.end,
        )

        with open(os.path.join(self.cache_path, filename), "w") as file:
            file.write(json.dumps(json_content))

        return self

    def load_from_cache(self) -> bool:
        if not os.path.exists(self.cache_path):
            return False

        for filename in os.listdir(self.cache_path):
            with open(os.path.join(self.cache_path, filename), "r") as file:
                print("loading from cache", filename)
                unformat_result = parse.parse(FILENAME_FORMAT, filename)

                if unformat_result is None or isinstance(unformat_result, parse.Match):
                    raise ValueError(
                        f"Filename {filename} does not match the expected format"
                    )

                unformat_result_dict = unformat_result.named

                start_epoch: int = int(unformat_result_dict["start_epoch"])
                end_epoch: int = int(unformat_result_dict["end_epoch"])

                self._precollected_epoch_intervals.append(
                    EpochInterval(start_epoch, end_epoch)
                )

                json_content: str = file.read()

                try:
                    parsed_json: list[dict] = json.loads(json_content)
                except json.JSONDecodeError:
                    print(ValueError(
                        f"File {filename} does not contain valid JSON data"
                    ))
                    continue

                for race_data in parsed_json:
                    self.data_samples.append(Race(**race_data))

        return True

    def __len__(self) -> int:
        return len(self.data_samples)
