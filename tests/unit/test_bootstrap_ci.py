"""Unit tests for bootstrap CI helper."""

from __future__ import annotations

from benchmark.evaluation.stats import bootstrap_ci, format_ci


class TestBootstrapCI:
    def test_basic_mean(self):
        values = [0.8, 0.7, 0.9, 0.85, 0.75, 0.8, 0.9, 0.85, 0.7, 0.8]
        point, lo, hi = bootstrap_ci(values, seed=42)
        assert 0.70 <= lo <= point <= hi <= 0.95

    def test_deterministic(self):
        """Same seed produces same result."""
        values = [0.6, 0.7, 0.8, 0.9, 1.0]
        r1 = bootstrap_ci(values, seed=123)
        r2 = bootstrap_ci(values, seed=123)
        assert r1 == r2

    def test_different_seeds_differ(self):
        """Different seeds may produce different CIs."""
        values = [0.5, 0.6, 0.7, 0.8, 0.9]
        r1 = bootstrap_ci(values, seed=1)
        r2 = bootstrap_ci(values, seed=999)
        # Point estimate should be the same (it's just the mean)
        assert r1[0] == r2[0]
        # CIs may differ (not guaranteed but highly likely)

    def test_empty_values(self):
        point, lo, hi = bootstrap_ci([], seed=42)
        assert point == 0.0
        assert lo == 0.0
        assert hi == 0.0

    def test_single_value(self):
        point, lo, hi = bootstrap_ci([0.75], seed=42)
        assert point == 0.75
        assert lo == 0.75
        assert hi == 0.75

    def test_all_same_values(self):
        point, lo, hi = bootstrap_ci([0.5, 0.5, 0.5, 0.5], seed=42)
        assert point == 0.5
        assert lo == 0.5
        assert hi == 0.5

    def test_ci_contains_point(self):
        """CI should always contain the point estimate."""
        values = [0.3, 0.5, 0.7, 0.4, 0.6, 0.8, 0.2, 0.9]
        point, lo, hi = bootstrap_ci(values, seed=42)
        assert lo <= point <= hi

    def test_wider_ci_with_more_variance(self):
        """More variable data should produce wider CIs."""
        tight = [0.50, 0.51, 0.49, 0.50, 0.51]
        wide = [0.10, 0.90, 0.20, 0.80, 0.50]
        _, t_lo, t_hi = bootstrap_ci(tight, seed=42)
        _, w_lo, w_hi = bootstrap_ci(wide, seed=42)
        assert (t_hi - t_lo) < (w_hi - w_lo)

    def test_n_bootstrap_parameter(self):
        values = [0.6, 0.7, 0.8, 0.9]
        # Should work with different bootstrap counts
        r1 = bootstrap_ci(values, n_bootstrap=100, seed=42)
        r2 = bootstrap_ci(values, n_bootstrap=10000, seed=42)
        # Both should produce valid intervals
        assert r1[1] <= r1[0] <= r1[2]
        assert r2[1] <= r2[0] <= r2[2]


class TestFormatCI:
    def test_percentage_format(self):
        result = format_ci(0.732, 0.651, 0.813)
        assert result == "73.2% [65.1, 81.3]"

    def test_decimal_format(self):
        result = format_ci(0.732, 0.651, 0.813, pct=False)
        assert result == "0.732 [0.651, 0.813]"

    def test_zero(self):
        result = format_ci(0.0, 0.0, 0.0)
        assert result == "0.0% [0.0, 0.0]"

    def test_perfect(self):
        result = format_ci(1.0, 1.0, 1.0)
        assert result == "100.0% [100.0, 100.0]"
