# coding: utf-8

"""
Test suite for djamix. Made with pytest.
"""


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
