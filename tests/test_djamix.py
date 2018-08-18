# coding: utf-8

"""
Test suite for djamix. Made with pytest.
"""

from datetime import date, datetime, time
import json

from django.test import Client
from django.urls import reverse
from django.template.exceptions import TemplateDoesNotExist

from pytest import raises, fixture

from djamix import start, rel


def test_two_complementary_colors():
    from djamix import two_random_complementary_colors
    color1, color2 = two_random_complementary_colors()
    assert all(0 <= c < 255 for c in color1)
    assert all((c2 == 255 - c1) for (c1, c2) in zip(color1, color2))


def test_DjamixJSONEncoder():
    from djamix import DjamixJSONEncoder, DjamixModel
    # dump date correctly
    assert json.dumps({'asd': date(2018, 3, 2)}, cls=DjamixJSONEncoder)\
        == '{"asd": "2018-03-02"}'

    class TestModel(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

    # qs/manager is not serializable, unless DjamixJSONEncoder is used
    with raises(TypeError):
        json.dumps({"qs": TestModel.objects.all()})

    json.dumps(
        {"qs": TestModel.objects.filter(id__lte=2)},
        cls=DjamixJSONEncoder
    )

    # However model is not serializble even with the proper Encoder...
    t = TestModel.objects.all()[0]
    with raises(TypeError):
        json.dumps({"item": t}, cls=DjamixJSONEncoder)

    # ... unless to_rich_json_representation is implemented
    class TestModel2(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

        def to_rich_json_representation(self):
            return vars(self)

    t = TestModel2.objects.all()[0]
    json.dumps({"item": t}, cls=DjamixJSONEncoder)


# ORM Tests
# ORM Tests
# ORM Tests

@fixture
def TestModel():
    from djamix import DjamixModel

    class TestModel(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/model1.yaml'

        def uppercase_baz(self):
            return self.baz.upper()

    return TestModel


@fixture
def client():
    return Client()


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


# =======================
# Testing views
# =======================

def test_basic_urls_setup():
    start()
    assert reverse('home') == '/'


def test_custom_basic_urls_setup(client):
    start('tests/fixtures/paths1.yaml')
    assert reverse('foobar') == '/foobar2/'
    with raises(TemplateDoesNotExist):
        client.get('/foobar2/')


def test_custom_basic_urls_with_custom_templates_setup(client):
    template_paths = [rel('../tests/templates/')]
    start('tests/fixtures/paths1.yaml', CUSTOM_TEMPLATE_DIRS=template_paths)
    assert reverse('foobar') == '/foobar2/'
    response = client.get('/foobar2/')
    assert response.status_code == 200
    assert response.content.decode('utf-8').strip() == "<h1>It's a BAR!</h1>"


def test_handling_custom_template_variables(client):
    template_paths = [rel('../tests/templates/')]
    context = {'hello': 'world'}  # NOQA
    start('tests/fixtures/paths1.yaml', CUSTOM_TEMPLATE_DIRS=template_paths)
    response = client.get(reverse('with_variables'))
    assert response.content.decode('utf-8').strip() == "hello == world"


def test_handling_custom_template_tags(client):
    template_paths = [rel('../tests/templates/')]

    def greeting(name):
        return f"Hello {name}"

    start('tests/fixtures/paths1.yaml', CUSTOM_TEMPLATE_DIRS=template_paths)
    response = client.get(reverse('with_templatetags'))
    assert response.content.decode('utf-8').strip()\
        == "greeting == Hello world"
