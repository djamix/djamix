# coding: utf-8

"""
Testing the data layer aka ORM-like API in djamix.
"""

from datetime import date, datetime, time
from pytest import raises, fixture


@fixture
def TestModel():
    from djamix import DjamixModel

    class TestModel(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

        def uppercase_baz(self):
            return self.baz.upper()

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

    t1 = [x.foo for x in TestModel.objects.order_by('type', 'color')]
    t2 = [3, 1, 7, 5]
    assert t1 == t2


def test_orm_predefined_ordering():

    from djamix import DjamixModel

    class TestModel(DjamixModel):
        class Meta:
            fixture = 'tests/fixtures/model1.yaml'
            ordering = ['type']

    t1 = [x.foo for x in TestModel.objects.all()]
    t2 = [1, 3, 5, 7]
    assert t1 == t2

    class TestModel(DjamixModel):
        class Meta:
            fixture = 'tests/fixtures/model1.yaml'
            ordering = ['type', 'color']

    t1 = [x.foo for x in TestModel.objects.all()]
    t2 = [3, 1, 7, 5]
    assert t1 == t2


def test_orm_groupby(TestModel):
    qs = TestModel.objects.groupby(lambda x: x.date.year)
    # there are three unique years but because qs is not ordered we still have
    # 4.
    assert len(qs) == 4
    qs = TestModel.objects.order_by('date').groupby(lambda x: x.date.year)
    assert len(qs) == 3
    assert dict(qs).keys() == {2018, 2019, 2020}
    assert len(dict(qs)[2018]) == 2


def test_filtering_and_ordering_via_custom_model_methods(TestModel):

    assert TestModel.objects.filter(uppercase_baz='HELLO').count() == 1

    assert [
        t.uppercase_baz() for t in TestModel.objects.order_by('uppercase_baz')
    ] == ['HELLO', 'RANDOM', 'TEXT', 'WORLD']


def test_custom_field_type_definition():

    from djamix import DjamixModel, Field

    class TestModel(DjamixModel):
        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

    assert isinstance(TestModel.objects.get(pk=1).date, date)

    class TestModel2(DjamixModel):
        date = Field(lambda x: datetime.combine(x, time.min))

        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

    assert isinstance(TestModel2.objects.get(pk=1).date, datetime)


def test_custom_model_method():

    from djamix import DjamixModel

    class TestModel(DjamixModel):
        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

        def dt(self):
            return datetime.combine(self.date, time.min)

    assert isinstance(TestModel.objects.get(pk=1).date, date)
    assert isinstance(TestModel.objects.get(pk=1).dt(), datetime)

    t = TestModel.objects.get(pk=1)
    assert t.date != t.dt()
    assert t.date == t.dt().date()


def test_fkeys():
    from djamix import DjamixModel, FK

    class TestModel1(DjamixModel):
        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

    class TestModel2(DjamixModel):
        test_model1 = FK(TestModel1, 'm1_text', 'baz')

        class Meta:
            fixture = 'tests/fixtures/model2.yaml'

    # This will work fine even though we have FK data in model2 that doesn't
    # match anything in model1...
    hello = TestModel2.objects.get(m1_text='hello')
    assert isinstance(hello.test_model1, TestModel1)
    assert hello.test_model1.foo == 5
    assert hello.test_model1.date == date(2018, 10, 13)
    assert hello.message == "This is 42"

    # ... however if enforce_schema is set to True, it will return DoesNotExist
    # if it finds any missing FK entries
    with raises(TestModel1.DoesNotExist):
        class TestModel3(DjamixModel):
            test_model1 = FK(TestModel1, 'm1_text', 'baz')

            class Meta:
                fixture = 'tests/fixtures/model2.yaml'
                enforce_schema = True

    # also, test default behaviour w/o specifying fields
    class TestModel4(DjamixModel):
        m1 = FK(TestModel1)

        class Meta:
            fixture = 'tests/fixtures/model2.yaml'

    assert isinstance(TestModel4.objects.get(pk=1).m1, TestModel1)
    assert isinstance(TestModel4.objects.get(pk=2).m1, TestModel1)

    assert TestModel4.objects.get(pk=1).m1.id == 1
    assert TestModel4.objects.get(pk=1).message == 'This is foo'
    assert TestModel4.objects.get(pk=1).m1.baz == 'random'


def test_autoseqid_behaviour():
    from djamix import DjamixModel

    class TestModel(DjamixModel):

        class Meta:
            pass

    t1 = TestModel()
    assert t1.id == 1

    t2 = TestModel()
    assert t2.id == 2

    t45 = TestModel(id=45)
    assert t45.id == 45

    t46 = TestModel()
    assert t46.id == 46

    with raises(AssertionError):
        TestModel(id=27)


def test_fkeys_api():
    from djamix import DjamixModel, FK

    class Parent(DjamixModel):

        class Meta:
            pass

    class Child(DjamixModel):
        parent = FK(Parent)

        class Meta:
            pass

    parent = Parent(name="Joe")
    child1 = Child(parent=parent, name="Kid")

    # check auto sequences
    assert child1.id == 1
    assert parent.id == 1
    assert child1.parent_id == 1

    assert child1.parent.name == "Joe"
