import os

from commonmark import commonmark
from collections import namedtuple

from turingarena.evallib.metadata import load_metadata


class Problem(namedtuple("Problem", ["contest", "name"])):
    @property
    def metadata(self):
        return load_metadata(self.path)

    @property
    def path(self):
        return os.path.join(self.contest.directory, self.name)

    @property
    def title(self):
        return self.metadata.get("problem", {}).get("title", self.name)

    @property
    def goals(self):
        return self.metadata.get("scoring", {}).get("goals", [])

    @property
    def files_dir(self):
        return os.path.join(self.path, "turingarena-files")

    @property
    def files_zip(self):
        return os.path.join(self.path, "files.zip")

    @property
    def statement(self):
        path = os.path.join(self.path, "statement.md")
        with open(path) as f:
            return commonmark(f.read())

    def as_json_data(self):
        return {
            "name": self.name,
            "contest": self.contest.name,
            "title": self.title,
            "statement": self.statement,
            "goals": self.goals,
        }
