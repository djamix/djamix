# coding: utf-8

"""
Testing djamix views, templatetags, etc.
"""

from pytest import raises, fixture
from django.test import Client
from django.urls import reverse
from django.template.exceptions import TemplateDoesNotExist

from djamix import start, rel


@fixture
def client():
    return Client()


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
