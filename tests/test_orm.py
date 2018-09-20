# coding: utf-8

"""
Testing the data layer aka ORM-like API in djamix.
"""

from datetime import date, datetime, time
from pytest import raises, fixture


@fixture
def Country():
    from djamix import DjamixModel

    class Country(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/countries.yaml'

        def uppercase_name(self):
            return self.name.upper()

    return Country


def test_basic_model_from_fixture(Country):
    assert Country.objects.all().count() == 3


def test_basic_integer_orm_lookups(Country):
    assert Country.objects.filter(country_code=44).count() == 1
    assert Country.objects.filter(country_code__gt=44).count() == 2
    assert Country.objects.filter(country_code__gte=44).count() == 3
    assert Country.objects.filter(country_code__lte=48).count() == 3
    assert Country.objects.filter(country_code__lt=48).count() == 2
    # assuming inclusive range, may change in the future
    assert Country.objects.filter(country_code__range=(44, 48)).count() == 3


def test_basic_boolean_orm_lookups(Country):
    assert Country.objects.filter(name__bool=True).count() == 3
    assert Country.objects.filter(name__bool=False).count() == 0
    assert Country.objects.filter(name__isnull=False).count() == 3
    assert Country.objects.filter(name__isnull=True).count() == 0
    assert Country.objects.filter(name__isnotnull=True).count() == 3
    assert Country.objects.filter(name__isnotnull=False).count() == 0


def test_basic_date_orm_lookups(Country):

    JANUARY = 1
    OCTOBER = 10

    assert Country.objects.filter(random_date__year=2018).count() == 1
    assert Country.objects.filter(random_date__year=2000).count() == 2

    assert Country.objects.filter(random_date__month=JANUARY).count() == 1
    assert Country.objects.filter(random_date__month=OCTOBER).count() == 1
    assert Country.objects.filter(
        random_date__gte=date(2000, 1, 1)
    ).count() == 3

    assert Country.objects.filter(
        random_date__gte=date(2018, 10, 13)
    ).count() == 1

    assert Country.objects.filter(
        random_date__gt=date(2018, 10, 13)
    ).count() == 0

    with raises(NotImplementedError):
        # TODO This will raise an exception because we don't support chained
        # dunder lookups yet, so it will try to resolve year__gte as one thing
        # and then fail to find any items with such property. However, once we
        # add the proper support it should return 4.
        assert Country.objects.filter(random_date__year__gte=2018).count() == 2


def test_chaining_orm_filter_calls(Country):
    OCTOBER = 10
    assert Country.objects\
        .filter(random_date__year=2018)\
        .filter(random_date__month=OCTOBER).count() == 1


def test_multiple_orm_filter_arguments_in_the_same_call(Country):
    qs = Country.objects.filter(continent='Europe')
    assert qs.count() == 2
    assert qs.filter(name='Poland').count() == 1
    assert qs.filter(name='Narnia').count() == 0


def test_orm_get(Country):
    assert Country.objects.get(name='Poland')
    assert Country.objects.get(name__startswith='P')

    with raises(Country.DoesNotExist):
        assert Country.objects.get(name='San Escobar')

    with raises(Country.MultipleObjectsReturned):
        assert Country.objects.get(continent='Europe')


def test_orm_order_by(Country):
    for country, code in zip(
        Country.objects.order_by('country_code'),
        [44, 46, 48]
    ):
        assert country.country_code == code

    for country, code in zip(
        Country.objects.order_by('-country_code'),
        [48, 46, 44]
    ):
        assert country.country_code == code

    dates = [
        ('Poland', date(2000, 1, 1)),
        ('Narnia', date(2000, 2, 2)),
        ('UK',     date(2018, 10, 13)),
    ]

    for country, (name, _) in zip(
        Country.objects.order_by('random_date'),
        dates
    ):
        assert country.name == name

    t1 = [c.name for c in Country.objects.order_by('-continent', '-name')]
    t2 = ['Narnia', 'UK', 'Poland']
    assert t1 == t2


def test_orm_predefined_ordering():

    from djamix import DjamixModel

    class Country(DjamixModel):
        class Meta:
            fixture = 'tests/fixtures/countries.yaml'
            ordering = ['country_code']

    t1 = [c.country_code for c in Country.objects.all()]
    t2 = [44, 46, 48]
    assert t1 == t2

    class Country(DjamixModel):
        class Meta:
            fixture = 'tests/fixtures/countries.yaml'
            ordering = ['-continent', '-country_code']

    t1 = [c.name for c in Country.objects.all()]
    t2 = ['Narnia', 'Poland', 'UK']
    assert t1 == t2


def test_orm_groupby(Country):
    qs = Country.objects.groupby(lambda c: c.random_date.year)
    # there are two unique years but because qs is not ordered we still have 3
    assert len(qs) == 3

    qs = Country.objects\
        .order_by('random_date')\
        .groupby(lambda c: c.random_date.year)

    assert len(qs) == 2
    assert dict(qs).keys() == {2000, 2018}
    assert len(dict(qs)[2018]) == 1


def test_filtering_and_ordering_via_custom_model_methods(Country):

    assert Country.objects.filter(uppercase_name='POLAND').count() == 1

    assert [
        t.uppercase_name()
        for t in Country.objects.order_by('uppercase_name')
    ] == ['NARNIA', 'POLAND', 'UK']


def test_custom_field_type_definition():

    from djamix import DjamixModel, Field

    class Country(DjamixModel):
        class Meta:
            fixture = 'tests/fixtures/countries.yaml'

    assert isinstance(Country.objects.get(pk=1).random_date, date)

    class CountryWithCustomField(DjamixModel):
        # field is still called random_date but actually returns a datetime
        random_date = Field(datetime, lambda x: datetime.combine(x, time.min))

        class Meta:
            fixture = 'tests/fixtures/countries.yaml'

    assert isinstance(
        CountryWithCustomField.objects.get(pk=1).random_date,
        datetime
    )


def test_custom_model_method():

    from djamix import DjamixModel

    class Country(DjamixModel):
        class Meta:
            fixture = 'tests/fixtures/countries.yaml'

        def dt(self):
            return datetime.combine(self.random_date, time.min)

    assert isinstance(Country.objects.get(pk=1).random_date, date)
    assert isinstance(Country.objects.get(pk=1).dt(), datetime)

    t = Country.objects.get(pk=1)
    assert t.random_date != t.dt()
    assert t.random_date == t.dt().date()


def test_empty_fixture_file_raises_fixture_error():
    from djamix import DjamixModel, FixtureError

    with raises(FixtureError):
        class EmptyModel(DjamixModel):
            class Meta:
                fixture = 'tests/fixtures/empty.yaml'


def test_fkeys():
    from djamix import DjamixModel, FK

    class Country(DjamixModel):
        class Meta:
            fixture = 'tests/fixtures/countries.yaml'

        def __str__(self):
            return self.name

    # This will work fine even though there are cities that link to countries
    # that doesn't exist.
    class City(DjamixModel):
        country = FK(Country, 'country_iso', 'iso')

        class Meta:
            fixture = 'tests/fixtures/cities.yaml'

        def __str__(self):
            return self.name

    krk = City.objects.get(name='Krakow')
    assert isinstance(krk.country, Country)
    assert krk.country.name == "Poland"
    assert krk.country.random_date == date(2000, 1, 1)
    assert krk.population == "1mil"

    # ... however if enforce_schema is set to True, it will return DoesNotExist
    # if it finds any missing FK entries
    with raises(Country.DoesNotExist):
        class City(DjamixModel):
            country = FK(Country, 'country_iso', 'iso')

            class Meta:
                fixture = 'tests/fixtures/cities.yaml'
                enforce_schema = True

    # also, test default behaviour w/o specifying fields
    class Town(DjamixModel):
        country = FK(Country)

        class Meta:
            fixture = 'tests/fixtures/towns.yaml'

    assert isinstance(Town.objects.get(pk=1).country, Country)
    assert isinstance(Town.objects.get(pk=2).country, Country)

    assert Town.objects.get(name='London').country.name == 'UK'
    assert Town.objects.get(name='London').country.location == 'NWE'


def test_autoseqid_behaviour():
    from djamix import DjamixModel

    class Foo(DjamixModel):

        class Meta:
            pass

    class Bar(DjamixModel):

        class Meta:
            pass

    f1 = Foo()
    assert f1.id == 1

    f2 = Foo()
    assert f2.id == 2

    f45 = Foo(id=45)
    assert f45.id == 45

    f46 = Foo()
    assert f46.id == 46

    b1 = Bar()
    assert b1.id == 1

    b2 = Bar()
    assert b2.id == 2

    f = Foo()
    assert f.id == 47

    with raises(AssertionError):
        Foo(id=27)


def test_fkeys_api():
    """Testing non-fixture based models"""
    from djamix import DjamixModel, FK

    class Parent(DjamixModel):

        class Meta:
            pass

    class Child(DjamixModel):
        parent = FK(Parent)

        class Meta:
            pass

    """
    TODO: implement reverse relationships in the DjamixModelMeta class.
    (something like django's foo.set_all()
    """
