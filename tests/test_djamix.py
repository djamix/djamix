# coding: utf-8

"""
Basic tests for things related mostly to project setup
"""

from datetime import date
import json


from pytest import raises


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

    class Country(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/countries.yaml'

    # qs/manager is not serializable, unless DjamixJSONEncoder is used
    with raises(TypeError):
        json.dumps({"qs": Country.objects.all()})

    json.dumps(
        {"qs": Country.objects.filter(id__lte=2)},
        cls=DjamixJSONEncoder
    )

    # However model is not serializble even with the proper Encoder...
    t = Country.objects.all()[0]
    with raises(TypeError):
        json.dumps({"item": t}, cls=DjamixJSONEncoder)

    # ... unless to_rich_json_representation is implemented
    class CountryWithSerializer(DjamixModel):

        class Meta:
            fixture = 'tests/fixtures/countries.yaml'

        def to_rich_json_representation(self):
            return vars(self)

    t = CountryWithSerializer.objects.all()[0]
    json.dumps({"item": t}, cls=DjamixJSONEncoder)
