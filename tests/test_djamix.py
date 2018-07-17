# coding: utf-8

"""
Test suite for djamix. Made with pytest.
"""

from datetime import date
from pytest import raises, fixture


def test_two_complementary_colors():
    from djamix import two_random_complementary_colors
    color1, color2 = two_random_complementary_colors()
    assert all(0 < c < 255 for c in color1)
    assert all((c2 == 255 - c1) for (c1, c2) in zip(color1, color2))


# ORM Tests
# ORM Tests
# ORM Tests

@fixture
def TestModel():
    from djamix import DjamixModel

    class TestModel(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

    return TestModel


def test_basic_model_from_fixture(TestModel):
    assert TestModel.objects.all().count() == 4


def test_basic_integer_orm_lookups(TestModel):
    assert TestModel.objects.filter(foo=5).count() == 1
    assert TestModel.objects.filter(foo__gt=5).count() == 1
    assert TestModel.objects.filter(foo__gte=5).count() == 2
    assert TestModel.objects.filter(foo__lte=5).count() == 3
    assert TestModel.objects.filter(foo__lt=5).count() == 2
    # assuming inclusive range, may change in the future
    assert TestModel.objects.filter(foo__range=(3, 5)).count() == 2


def test_basic_boolean_orm_lookups(TestModel):
    assert TestModel.objects.filter(foo__bool=True).count() == 4
    assert TestModel.objects.filter(foo__bool=False).count() == 0
    assert TestModel.objects.filter(foo__isnull=False).count() == 4
    assert TestModel.objects.filter(foo__isnull=True).count() == 0
    assert TestModel.objects.filter(foo__isnotnull=True).count() == 4
    assert TestModel.objects.filter(foo__isnotnull=False).count() == 0


def test_basic_date_orm_lookups(TestModel):

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


def test_chaining_orm_filter_calls(TestModel):
    JULY = 7
    assert TestModel.objects\
        .filter(date__year=2018)\
        .filter(date__month=JULY).count() == 1


def test_multiple_orm_filter_arguments_in_the_same_call(TestModel):
    assert TestModel.objects\
        .filter(baz='hello', date__year=2018).count() == 1

    assert TestModel.objects\
        .filter(date__year=2018, baz='hello').count() == 1

    assert TestModel.objects\
        .filter(date__year=2018, bar__gte=0).count() == 2


def test_orm_get(TestModel):
    assert TestModel.objects.get(baz='hello')
    assert TestModel.objects.get(baz__startswith='he')

    with raises(TestModel.DoesNotExist):
        assert TestModel.objects.get(baz='helloworld')

    with raises(TestModel.MultipleObjectsReturned):
        assert TestModel.objects.get(date__year=2018)


def test_orm_order_by(TestModel):
    for x, y in zip(TestModel.objects.order_by('bar'), [2, 4, 6, 8]):
        assert x.bar == y

    for x, y in zip(TestModel.objects.order_by('-foo'), [7, 5, 3, 1]):
        assert x.foo == y

    reversed_baz = ["world", "text", "random", "hello"]
    for x, y in zip(TestModel.objects.order_by('-baz'), reversed_baz):
        assert x.baz == y

    dates = [date(2018, 7, 13), date(2018, 10, 13), date(2019, 7, 13),
             date(2020, 7, 13)]

    for x, y in zip(TestModel.objects.order_by('date'), dates):
        assert x.date == y


def test_orm_groupby(TestModel):
    qs = TestModel.objects.groupby(lambda x: x.date.year)
    # there are three unique years but because qs is not ordered we still have
    # 4.
    assert len(qs) == 4
    qs = TestModel.objects.order_by('date').groupby(lambda x: x.date.year)
    assert len(qs) == 3
    assert dict(qs).keys() == {2018, 2019, 2020}
    assert len(dict(qs)[2018]) == 2
