# Copyright © 2023 Pathway

import itertools
from collections import defaultdict
from collections.abc import Iterator

from pysat.solvers import Solver

from pathway.internals.universe import Universe


class UniverseSolver:
    universe_vars: dict[Universe, int]
    var_counter: Iterator[int]
    solver: Solver

    def __init__(self):
        self.solver = Solver(name="g4")
        self.var_counter = itertools.count(start=1)
        self.universe_vars = defaultdict(lambda: next(self.var_counter))

    def register_as_equal(self, left: Universe, right: Universe) -> None:
        self.register_as_subset(left, right)
        self.register_as_subset(right, left)

    def register_as_subset(self, subset: Universe, superset: Universe) -> None:
        varA = self.universe_vars[subset]
        varB = self.universe_vars[superset]
        # varA => varB
        self.solver.add_clause([-varA, varB])

    def get_subset(self, superset: Universe) -> Universe:
        subset = Universe()
        self.register_as_subset(subset, superset)
        return subset

    def get_superset(self, subset: Universe) -> Universe:
        superset = Universe()
        self.register_as_subset(subset, superset)
        return superset

    def register_as_difference(
        self, result: Universe, setLeft: Universe, setRight: Universe
    ) -> None:
        """result = setLeft - setRight"""
        self.register_as_subset(result, setLeft)
        self.register_as_disjoint(result, setRight)
        varResult = self.universe_vars[result]
        varLeft = self.universe_vars[setLeft]
        varRight = self.universe_vars[setRight]
        # (varLeft and ~varRight) => varResult
        self.solver.add_clause([varResult, -varLeft, varRight])

    def get_difference(self, setLeft: Universe, setRight: Universe) -> Universe:
        result = Universe()
        self.register_as_difference(result, setLeft, setRight)
        return result

    def register_as_intersection(self, result: Universe, *args: Universe) -> None:
        for arg in args:
            self.register_as_subset(result, arg)

        result_var = self.universe_vars[result]
        args_var = [self.universe_vars[arg] for arg in args]
        # (arg1 and arg2 and ...) => result
        self.solver.add_clause([result_var, *[-arg_var for arg_var in args_var]])

    def get_intersection(self, *args: Universe) -> Universe:
        for arg in args:
            if all(arg.is_subset_of(other) for other in args):
                return arg
        result = Universe()
        self.register_as_intersection(result, *args)
        return result

    def register_as_union(self, result: Universe, *args: Universe) -> None:
        for arg in args:
            self.register_as_subset(arg, result)

        result_var = self.universe_vars[result]
        args_var = [self.universe_vars[arg] for arg in args]
        # result => (arg1 or arg2 or ...)
        self.solver.add_clause([-result_var, *args_var])

    def get_union(self, *args: Universe) -> Universe:
        for arg in args:
            if all(other.is_subset_of(arg) for other in args):
                return arg
        result = Universe()
        self.register_as_union(result, *args)
        return result

    def query_is_subset(self, subset: Universe, superset: Universe) -> bool:
        varA = self.universe_vars[subset]
        varB = self.universe_vars[superset]
        # assume varA and ~varB and check if fails
        return not self.solver.solve(assumptions=[varA, -varB])

    def query_are_equal(self, setA: Universe, setB: Universe) -> bool:
        return self.query_is_subset(setA, setB) and self.query_is_subset(setB, setA)

    def query_are_disjoint(self, *args: Universe) -> bool:
        # TODO: this code might be doable with O(n) checks, not O(n^2)
        vars = [self.universe_vars[arg] for arg in args]
        for i in range(len(vars)):
            for j in range(i):
                if self.solver.solve(assumptions=[vars[i], vars[j]]):
                    return False
        return True

    def register_as_disjoint(self, *args: Universe) -> None:
        vars = [self.universe_vars[arg] for arg in args]
        for i in range(len(vars)):
            for j in range(i):
                # varI => ~varJ
                self.solver.add_clause([-vars[i], -vars[j]])

    def register_as_empty(self, setA: Universe) -> None:
        varA = self.universe_vars[setA]
        self.solver.add_clause([-varA])
