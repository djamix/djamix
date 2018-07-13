# coding: utf-8

"""
Test suite for djamix. Made with pytest.
"""


def test_two_complementary_colors():
    from djamix import two_random_complementary_colors
    color1, color2 = two_random_complementary_colors()
    assert all(0 < c < 255 for c in color1)
    assert all((c2 == 255 - c1) for (c1, c2) in zip(color1, color2))
