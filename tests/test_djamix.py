# coding: utf-8

"""
Test suite for djamix. Made with pytest.
"""

from datetime import date
from pytest import raises


def test_two_complementary_colors():
    from djamix import two_random_complementary_colors
    color1, color2 = two_random_complementary_colors()
    assert all(0 < c < 255 for c in color1)
    assert all((c2 == 255 - c1) for (c1, c2) in zip(color1, color2))


# ORM Tests
# ORM Tests
# ORM Tests

def test_basic_model_from_fixture():
    from djamix import DjamixModel

    class TestModel(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

    assert TestModel.objects.all().count() == 4


def test_basic_integer_orm_lookups():
    from djamix import DjamixModel

    class TestModel(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

    assert TestModel.objects.filter(foo=5).count() == 1
    assert TestModel.objects.filter(foo__gt=5).count() == 1
    assert TestModel.objects.filter(foo__gte=5).count() == 2
    assert TestModel.objects.filter(foo__lte=5).count() == 3
    assert TestModel.objects.filter(foo__lt=5).count() == 2
    # assuming inclusive range, may change in the future
    assert TestModel.objects.filter(foo__range=(3, 5)).count() == 2


def test_basic_boolean_orm_lookups():
    from djamix import DjamixModel

    class TestModel(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

    assert TestModel.objects.filter(foo__bool=True).count() == 4
    assert TestModel.objects.filter(foo__bool=False).count() == 0
    assert TestModel.objects.filter(foo__isnull=False).count() == 4
    assert TestModel.objects.filter(foo__isnull=True).count() == 0
    assert TestModel.objects.filter(foo__isnotnull=True).count() == 4
    assert TestModel.objects.filter(foo__isnotnull=False).count() == 0


def test_basic_date_orm_lookups():
    from djamix import DjamixModel

    class TestModel(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

    JULY = 7
    OCTOBER = 10
    assert TestModel.objects.filter(date__year=2018).count() == 2

    assert TestModel.objects.filter(date__month=JULY).count() == 3
    assert TestModel.objects.filter(date__month=OCTOBER).count() == 1
    assert TestModel.objects.filter(date__gte=date(2018, 6, 4)).count() == 4
    assert TestModel.objects.filter(date__gte=date(2019, 6, 4)).count() == 2

    with raises(NotImplementedError):
        # TODO This will raise an exception because we don't support chained
        # dunder lookups yet, so it will try to resolve year__gte as one thing
        # and then fail to find any items with such property. However, once we
        # add the proper support it should return 4.
        assert TestModel.objects.filter(date__year__gte=2018).count() == 4


def test_multiple_orm_filter_arguments_in_the_same_call():
    from djamix import DjamixModel

    class TestModel(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

    JULY = 7
    assert TestModel.objects\
        .filter(date__year=2018)\
        .filter(date__month=JULY).count() == 1

    assert TestModel.objects\
        .filter(baz='hello', date__year=2018).count() == 1

    assert TestModel.objects\
        .filter(date__year=2018, baz='hello').count() == 1
