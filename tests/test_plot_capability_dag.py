"""Tests for aedist.plot_capability_dag.compute_matrix — pairwise arrival ordering."""

from datetime import date

import numpy as np

from aedist.plot_capability_dag import N_STAGES, compute_matrix


def test_compute_matrix_shape() -> None:
    frac, counts = compute_matrix({})
    assert frac.shape == (N_STAGES, N_STAGES)
    assert counts.shape == (N_STAGES, N_STAGES)


def test_diagonal_is_nan_and_zero() -> None:
    lab_dates = {"labA": {1: date(2020, 1, 1), 2: date(2021, 1, 1)}}
    frac, counts = compute_matrix(lab_dates)
    assert np.isnan(frac[0, 0])
    assert counts[0, 0] == 0


def test_consistent_ordering_gives_full_fraction() -> None:
    # Two labs both reach stage 1 before stage 2.
    lab_dates = {
        "labA": {1: date(2020, 1, 1), 2: date(2021, 1, 1)},
        "labB": {1: date(2019, 1, 1), 2: date(2020, 1, 1)},
    }
    frac, counts = compute_matrix(lab_dates)
    assert counts[0, 1] == 2
    assert frac[0, 1] == 1.0
    assert frac[1, 0] == 0.0


def test_tie_splits_evenly() -> None:
    lab_dates = {
        "labA": {1: date(2020, 1, 1), 2: date(2020, 1, 1)},
        "labB": {1: date(2020, 1, 1), 2: date(2020, 1, 1)},
    }
    frac, counts = compute_matrix(lab_dates)
    assert counts[0, 1] == 2
    assert frac[0, 1] == 0.5


def test_single_observation_left_nan() -> None:
    # Only one lab has both stages -> n_total < 2 -> fraction stays NaN.
    lab_dates = {"labA": {1: date(2020, 1, 1), 2: date(2021, 1, 1)}}
    frac, counts = compute_matrix(lab_dates)
    assert counts[0, 1] == 1
    assert np.isnan(frac[0, 1])
