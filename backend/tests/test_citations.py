from services.citations import renumber_citations


def test_renumbers_by_first_use_and_drops_uncited():
    text, used = renumber_citations("B is true [3]. A is true [1].", source_count=4)
    assert text == "B is true [1]. A is true [2]." and used == [3, 1]


def test_repeats_collapse():
    text, used = renumber_citations("Fact [2][2]. Again [2] [2].", source_count=2)
    assert text == "Fact [1]. Again [1]." and used == [2]


def test_lists_and_ranges_expand():
    text, used = renumber_citations("See [1, 3] and [2-3].", source_count=3)
    assert text == "See [1][2] and [3][2]." and used == [1, 3, 2]


def test_math_and_years_are_untouched():
    answer = "Values lie in $[0, 1]$ as in [2017], see [1]. $$x_{[1]}$$"
    text, used = renumber_citations(answer, source_count=1)
    assert text == "Values lie in $[0, 1]$ as in [2017], see [1]. $$x_{[1]}$$" and used == [1]
