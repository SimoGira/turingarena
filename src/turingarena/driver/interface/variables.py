from collections import namedtuple
from enum import Enum


class Variable(namedtuple("Variable", ["name"])):
    __slots__ = []

    def as_reference(self):
        return Reference(self, index_count=0)


Reference = namedtuple("Reference", ["variable", "index_count"])

ReferenceDirection = Enum("ReferenceDirection", names=["DOWNWARD", "UPWARD"])

ReferenceDeclaration = namedtuple("ReferenceDeclaration", ["reference", "dimensions"])
ReferenceResolution = namedtuple("ReferenceResolution", ["reference"])

VariableDeclaration = namedtuple("VariableDeclaration", ["variable", "dimensions"])
VariableAllocation = namedtuple("VariableAllocation", ["variable", "indexes", "size", "dimensions"])
