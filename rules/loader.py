# rules/loader.py
import json
import os
from copy import deepcopy

RULES_DIR = os.path.dirname(__file__)

class RuleLoader:

    def __init__(self):
        self.cache = {}

    def _path(self, name):
        return os.path.join(RULES_DIR, name)

    def load(self, filename):
        if filename in self.cache:
            return deepcopy(self.cache[filename])

        path = self._path(filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Rule file não encontrado: {filename}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.cache[filename] = data
        return deepcopy(data)

    def save(self, filename, data):
        path = self._path(filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.cache[filename] = data

    def get_strategies(self, filename):
        data = self.load(filename)
        return data.get("strategies", [])

    def update_score(self, filename, strategy_name, delta):
        data = self.load(filename)

        for s in data.get("strategies", []):
            if s.get("name") == strategy_name:
                s["score"] = round(max(0, s.get("score", 0) + delta), 3)

        # ordena por score
        data["strategies"].sort(
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        self.save(filename, data)

    def add_strategy(self, filename, strategy):
        data = self.load(filename)

        strategy = deepcopy(strategy)
        strategy.setdefault("score", 0.5)

        data.setdefault("strategies", []).insert(0, strategy)
        data["version"] = data.get("version", 1) + 1

        self.save(filename, data)