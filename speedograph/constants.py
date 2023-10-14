from __future__ import annotations


TYPERACER_START_EPOCH = 1201845600  # Before March 2008 (feb-1-2008)
COLLECTION_WINDOW_EPOCH = 2629743 * 3  # 3 months
CACHE_DATA_PATH = "data/cache/{username}"
FILENAME_FORMAT = "{start_epoch}_{end_epoch}.json"
API_URL = "https://data.typeracer.com/games?playerId=tr:{username}&universe=play&startDate={start_epoch}&endDate={end_epoch}"
