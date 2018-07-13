#!/usr/bin/env python3

"""
This is main djamix file.
"""

from collections import defaultdict, OrderedDict
from functools import cmp_to_key
from operator import attrgetter as A
from urllib.parse import urlencode
from uuid import NAMESPACE_URL, uuid4, uuid5
import csv
import code
import datetime
import inspect
import itertools
import json
import os
import operator
import random
import shutil
import sys

from django.conf import settings
from django.conf.urls.static import static
from django.core.management import execute_from_command_line
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.template import Library
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.template.defaultfilters import slugify
from django.urls import path, reverse
from django.utils import autoreload
from django.utils.lorem_ipsum import words

import yaml
from faker import Faker

fake = Faker()
register = Library()

urlpatterns = []
djamix_models = {}
registered_functions = {}
global_context = {}
USER_COMMANDS = {}

MEDIA_URL = "/media/"
MEDIA_ROOT = "media/"

DEBUG = False


def two_random_complementary_colors():
    """
    This is not very useful but we use it on the default template to randomise
    bg an text color every time the server reloads
    """
    def color():
        return random.randrange(0, 255)
    R, G, B = color(), color(), color()
    opposite_color = 255 - R, 255 - G, 255 - B
    return (R, G, B), opposite_color


BGCOLOR, TXTCOLOR = two_random_complementary_colors()
DEFAULT_TEMPLATE_NAME = 'hakunamatata.html'
DEFAULT_TEMPLATE_CONTENT = """
<html>
<body>
<style>
 body { background: rgb%(bodybg)s; color: rgb%(txtcolor)s;
        font-family: monospace; }
 h1 { margin-top: 3em; text-align: center; font-size: 5em; }
</style>
<h1>Hakuna Matata!</h1>
</body>
</html>
""".strip() % {'bodybg': BGCOLOR, 'txtcolor': TXTCOLOR}


class DjamixJSONEncoder(DjangoJSONEncoder):

    def default(self, o):
        if hasattr(o, 'to_rich_json_representation'):
            return o.to_rich_json_representation()

        if isinstance(o, datetime.date):
            return str(o)

        return super().default(o)


# ---------
# Data part
# Data part
# Data part
# ---------

class Field:
    """
    Allows for easier marking of field types. Doesn't do much itself except for
    keeping type information.
    """

    def __init__(self, type):
        self.type = type


class FK:

    def __init__(self, target_class, from_field=None, to_field=None):
        self.target_class = target_class
        self.from_field = from_field
        self.to_field = to_field

    def as_fk_description(self, new_local_field):
        if not (self.from_field or self.to_field):
            return self.target_class

        return {
            self.from_field: (
                new_local_field,
                self.target_class,
                self.to_field,
            )
        }


def make_accessible_name(name):
    """
    The goal here is to take a random name, like "Meetup ID", and turn it into
    something we can accesss as a python attribute, for example meetup_id (or
    meetupId if camel case is what you want.

    Idea based on what javascript is doing in the browser
    """
    return slugify(name).replace('-', '_')


def multi_attr_sort(items, columns):
    # copied and adapted from
    # https://stackoverflow.com/questions/1143671/
    # /python-sorting-list-of-dictionaries-by-multiple-keys

    def cmp(a, b):
        if callable(a):
            a = a()
        if callable(b):
            b = b()
        return (a > b) - (a < b)

    comparers = [(
        (A(c[1:].strip()), -1) if c.startswith('-') else (A(c.strip()), 1)
    ) for c in columns]

    def comparer(left, right):
        for fn, mult in comparers:
            result = cmp(fn(left), fn(right))
            if result:
                return mult * result
        else:
            return 0

    return sorted(items, key=cmp_to_key(comparer))


def filter_including_callables(obj, key, value, operation=operator.eq):
    thing = getattr(obj, key, None)
    if callable(thing):
        return operation(thing(), value)
    return operation(thing, value)


FILTER_FUNCTIONS = {
    # strings
    'startswith':  lambda x, y: x.startswith(y),
    'istartswith': lambda x, y: x.lower().startswith(y.lower()),
    'endswith':    lambda x, y: x.endswith(y),
    'iendswith':   lambda x, y: x.lower().endswith(y.lower()),
    'exact':       lambda x, y: x == y,
    'iexact':      lambda x, y: x.lower() == y.lower(),
    'contains':    lambda x, y: y in x,
    'icontains':   lambda x, y: y.lower() in x.lower(),

    # nulls
    'bool':        lambda x, y: bool(x) == y,
    'isnull':      lambda x, y: (not bool(x)) == y,
    'isnotnull':   lambda x, y: bool(x) == y,

    # numbers
    'gt':          lambda x, y: x > y,
    'gte':         lambda x, y: x >= y,
    'lt':          lambda x, y: x < y,
    'lte':         lambda x, y: x <= y,

    # dates
    # TODO(artcz): Not sure if range should be inclusive or not.
    'range':       lambda x, y: y[0] <= x <= y[1],
    'year':        lambda x, y: x.year  == y,
    'month':       lambda x, y: x.month == y,
}


class DjamixManager:

    def __init__(self, records, model_class, ordering=None, previous=None):
        self.previous = previous
        self.model_class = model_class

        if not ordering:
            self.ordering = getattr(model_class.Meta, 'ordering', None)
        else:
            self.ordering = ordering

        if (not ordering) and self.ordering:
            self._records = multi_attr_sort(records, self.ordering)
        else:
            self._records = records

    def _clone(self, new_records, **kwargs):
        return self.__class__(new_records,
                              model_class=self.model_class,
                              previous=self,
                              **kwargs)

    def __getitem__(self, item):
        return self._records[item]

    def __iter__(self):
        return iter(self._records)

    def __len__(self):
        return len(self._records)

    def __add__(self, other):
        return self._clone(new_records=self._records + other._records)

    def fake(self, count):
        fake_records = []
        latest_seqid = self.order_by("-pk")[0].id

        def fake_value(type, field_name):
            if type == int:
                return fake.pyint()
            elif type == float:
                return fake.pyfloat()
            elif type == bool:
                return fake.pybool()
            elif type == str:
                custom_faker = getattr(fake, field_name, None)
                if custom_faker:
                    return custom_faker()
                else:
                    return words(3, common=False)
                    return fake.pystr()
            elif type == datetime.date:
                return fake.date_object()
            else:
                raise ValueError("UNKOWN TYPE!", type)

        for i in range(count):
            kwargs = {
                field_name: fake_value(field_type, field_name)
                for field_name, field_type in self.model_class._schema.items()
            }
            kwargs['uuid'] = str(uuid4())
            kwargs['pk'] = latest_seqid
            kwargs['id'] = latest_seqid
            latest_seqid += 1
            fake_record = self.model_class(**kwargs)
            fake_records.append(fake_record)

        return self._clone(fake_records)

    def precreate_fake(self, count):
        fake = self.fake(count)
        self._records += fake._records

    def all(self):
        return self

    def get(self, **kwargs):
        filtered = self.filter(**kwargs)
        if len(filtered) > 1:
            raise ValueError("It didnt' return 1 object it returned %s" %
                             len(filtered))
        elif len(filtered) == 0:
            raise ValueError("Not such %s with %s" % (
                self.model_class.__name__,
                kwargs
            ))
        else:
            return filtered[0]

    def filter(self, **kwargs):
        filters = []
        for key, value in kwargs.items():
            elements = key.split("__")
            if len(elements) == 1:
                filters.append(
                    lambda x: filter_including_callables(x, key, value)
                )

            if len(elements) == 2:
                try:
                    function = FILTER_FUNCTIONS[elements[1]]
                except KeyError:
                    raise ValueError(
                        "Unsupported lookup type `%s`" % elements[1]
                    )

                filters.append(
                    lambda x: filter_including_callables(
                        x, elements[0], value, operation=function
                    )
                )

        filtered = []
        for r in self.all():
            for f in filters:
                if f(r):
                    # skip duplicates
                    if r not in filtered:
                        filtered.append(r)

        return self._clone(filtered)

    def count(self):
        return len(self)

    def order_by(self, *sorting):
        if len(sorting) == 1 and sorting[0] == '?':
            # return random order
            return self._clone(
                sorted(self._records, key=lambda x: random.random()),
                ordering=sorting,
            )
        new_records = multi_attr_sort(self._records, sorting)
        return self._clone(new_records, ordering=sorting)

    def groupby(self, keyfunc):
        """
        If you wanted to use itertools.groupby result in the templates it would
        break due to templates wanting to know the length (which Groupers do
        not have).
        More explanation here:
            https://stackoverflow.com/questions/6906593/
            /itertools-groupby-in-a-django-template

        One of the solutions is to repackage as a list of tuples.
        """
        return [(x, list(y)) for x, y in itertools.groupby(self, keyfunc)]

    def sum(self, *fields):
        """
        This is a simpler implementation of .aggregate(Sum('f1'), Sum('f2')
        To be upgraded later for full implementation of aggregates
        """
        sums = defaultdict(int)
        for r in self:
            for f in fields:
                sums[f] += getattr(r, f)

        # flatten to regular dict instead of defaultdict
        return dict(sums)

    def to_rich_json_representation(self):
        # FIXME: fix the name
        out = [record.to_dict() for record in self]
        return out


class DjamixModelMeta(type):

    @staticmethod
    def extract_managers(body):
        """
        This is here only because of namespacing under DjamixModelMeta

        Could be standalone
        """

        managers = {}
        for k, v in body.items():
            # TODO: maybe in the future we could/should intantiate managers,
            # just like in django?
            if inspect.isclass(v) and issubclass(v, DjamixManager):
                managers[k] = v

        return managers

    def __new__(cls, new_class_name, bases, body):
        if 'Meta' not in body:
            raise TypeError("Meta not defined")

        if DEBUG:
            print("Creating ", new_class_name, bases, body)
        base_cls = super().__new__(cls, new_class_name, bases, body)

        fixture       = getattr(body['Meta'], 'fixture', None)
        delimiter     = getattr(body['Meta'], 'delimiter', None)

        field_types = {}
        # dynamic filed_types...
        for key, value in body.items():
            if isinstance(value, Field):
                field_types[key] = value.type

        # TODO get a proper FK implementation for now replacing marking with
        # Meta.fkeys to using FK for producing the same dictionary
        fkeys = {}
        for key, value in body.items():
            if isinstance(value, FK):
                fkeys.update(value.as_fk_description(key))

        managers = cls.extract_managers(body)
        if 'objects' not in managers:
            managers['objects'] = DjamixManager

        if not fixture:
            if new_class_name != 'DjamixModel':
                # Handling special cases if user-defined model doesnt have
                # DataFile provided
                raise ValueError("No Meta.fixture provided for %s",
                                 new_class_name)
            return base_cls

        autoreload._cached_filenames.append(fixture)

        with open(fixture) as file:
            # TODO: add mimetype based load of CSV and JSON files
            if fixture.split('.')[-1] in ['yml', 'yaml']:
                records = yaml.load(file)
            elif fixture.split('.')[-1].lower() in ['csv', 'tsv']:
                records = list(csv.DictReader(file, delimiter=delimiter))
            else:
                raise ValueError("Unusported fixture type")

        setattr(base_cls, 'BASE_FIELDS', [])
        # better name maybe? for accessing via []
        setattr(base_cls, '_raw_fields', {})
        setattr(base_cls, '_schema', OrderedDict())
        setattr(base_cls, '_fkeys', {})

        # fill with data
        objects = []
        # using this instead of enumerate because it might be overwritten by a
        # value and then we want to just keep incrementing
        seqid = 1
        base_cls.BASE_FIELDS.append('id')
        base_cls.BASE_FIELDS.append('pk')
        base_cls._schema['id'] = int
        base_cls._schema['pk'] = int
        for r in records:
            c = base_cls()

            for k, v in r.items():
                # this is useful for CSVs that have keys with spaces, etc.
                accessible_name = make_accessible_name(k)

                if k not in base_cls.BASE_FIELDS:
                    base_cls.BASE_FIELDS.append(accessible_name)
                    base_cls._raw_fields[k] = accessible_name

                # same as BASEFIELDS once works, remove basefields...
                if accessible_name in field_types:
                    v = field_types[accessible_name](v)

                if k not in base_cls._schema:
                    if k in field_types:
                        base_cls.schema[accessible_name] = field_types[k]
                    else:
                        base_cls._schema[accessible_name] = type(v)

                setattr(c, accessible_name, v)

                if fkeys and k in fkeys:

                    if isinstance(fkeys[k], tuple):
                        # "field_name": (
                        #     'new_field', TargetClass, 'target_field'
                        # )
                        assert len(fkeys[k]) == 3
                        new_local_field, target_class, target_field = fkeys[k]

                        if v:
                            v = target_class.objects.get(**{target_field: v})
                        else:
                            v = None

                        setattr(c, new_local_field, v)
                        c._fkeys[new_local_field] = (target_class,
                                                     target_field)

                    elif k.endswith('_id'):
                        v = fkeys[k].objects.get(id=v)
                        setattr(c, k[:-3], v)
                        c._fkeys[k] = (fkeys[k], 'id')

                    elif k.endswith('_uuid'):
                        v = fkeys[k].objects.get(uuid=v)
                        setattr(c, k[:-5], v)
                        c._fkeys[k] = (fkeys[k], 'uuid')

                    # TODO: figure out reverse managers (aka _set)

            if 'uuid' not in r.keys():
                # create a stable string represantion of the record
                # if it's not changed it will have the same uuid
                sorted_record = ''.join(sorted(str(r)))
                # using random, but static namespace
                setattr(c, 'uuid', str(uuid5(NAMESPACE_URL, sorted_record)))

            if 'id' in r.keys():
                seqid = r['id']

            setattr(c, 'id', seqid)
            setattr(c, 'pk', seqid)
            seqid += 1

            objects.append(c)

        for manager_name, manager_class in managers.items():
            setattr(base_cls, manager_name, manager_class(objects, base_cls))

        djamix_models[new_class_name] = base_cls
        print_model_summary(new_class_name, base_cls)
        return base_cls


def print_model_summary(name, cls):
    print("Created %s" % name)
    print('\n'.join(
        '\t%s -> %s' % (field, type.__name__)
        for field, type in cls._schema.items()
    ))
    print('\n'.join(
        '\t%s -> FK(%s, %s)' % (fk, description[0].__name__, description[1])
        for fk, description in cls._fkeys.items()
    ))


class DjamixModel(metaclass=DjamixModelMeta):

    class Meta:
        pass

    def __init__(self, **kwargs):
        super().__init__()
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.uuid)

    def to_dict(self):
        return {f: getattr(self, f, None) for f in self.BASE_FIELDS}

    def dump_to_yaml(self):
        return yaml.dump(self.to_dict())


class DjamixCompositeModelMeta(type):

    def __new__(cls, new_class_name, bases, body):
        if 'Meta' not in body:
            raise TypeError("Meta not defined")

        base_cls = super().__new__(cls, new_class_name, bases, body)

        compose_from  = getattr(body['Meta'], 'compose_from', None)

        managers = DjamixModelMeta.extract_managers(body)
        if 'objects' not in managers:
            managers['objects'] = DjamixManager

        if not compose_from:
            return base_cls

        setattr(base_cls, 'BASE_FIELDS', [])
        setattr(base_cls, '_schema', [])

        # fill with data
        objects = []
        # using this instead of enumerate because it might be overwritten by a
        # value and then we want to just keep incrementing
        seqid = 1
        records = itertools.chain(
            *(model.objects.all()._records for model in compose_from)
        )
        union_of_base_fields = list(
            set().union(*(m.BASE_FIELDS for m in compose_from))
        )
        # print("\nUNION OF BFIELDS", union_of_base_fields)
        for r in records:
            c = base_cls()

            setattr(c, 'BASE_FIELDS', union_of_base_fields)
            setattr(c, 'id', seqid)
            setattr(c, '_source', r)
            seqid += 1

            uuid = str(uuid5(NAMESPACE_URL, r.uuid))
            setattr(c, 'uuid', uuid)

            for f in union_of_base_fields:
                setattr(c, f, getattr(r, f, None))

            objects.append(c)

        for manager_name, manager_class in managers.items():
            mgr = manager_class(objects, base_cls)
            setattr(base_cls, manager_name, mgr)

        djamix_models[new_class_name] = cls
        return base_cls


class CompositeModel(metaclass=DjamixCompositeModelMeta):

    class Meta:
        pass


# --------------
# VIEWS PART
# VIEWS PART
# VIEWS PART
# --------------

def media_url(media_path):
    """
    This is a template tag that's using MEDIA_URL and returns a relative path
    to a given media (as string) to fromn that globally defined URL.
    TODO: reword this docstring
    """
    return MEDIA_URL.rstrip('/') + '/' + media_path.lstrip('/')


def async_include(template_name, **context):
    """
    This is a templatetag that produces auto-including javascript
    """
    guid = uuid4()
    ctx = dict(template_name=template_name, **context)
    url = "/__async_include__/?%s" % urlencode(ctx)
    return render_to_string(
        "_async_include_template.html",
        dict(url=url, guid=guid, **context)
    )


def async_load(request):
    """
    This is a view that takes arguments as query strings, then render template
    with a given context and returns that back to the browser.

    All the paramters are going to be query strings for simplicity
    """
    params = {}
    # this is a bit of ugly magic to get single values instead of lists
    for k, v in request.GET.items():
        params[k] = request.GET.get(k)

    return TemplateResponse(request, params['template'], params)


def dump(format, data):
    """
    Dump to text format (JSON and CSV supported)
    """
    if format == 'JSON':
        return json.dumps(data, cls=DjamixJSONEncoder)

    if format == 'CSV':
        raise NotImplementedError


def data_to_response(format, function_name, **params):
    assert format in ['JSON', 'CSV']
    # FIXME/TODO: add support for CSV
    content_type = {
        'CSV': "text/csv",
        'JSON': "application/json",
    }
    data = registered_functions[function_name](**params)
    return HttpResponse(dump(format, data),
                        content_type=content_type[format])


def async_data(request):
    """
    That's a view

    If you want to use it in templates just point to a url
        {% url "async_data" %}?data_format=JSON&function_name=whatever&p1=foo

    or... use {% async_data_url %} templatetag

    Similar to async_load but instead of html returns asked data format
    """
    if 'function_name' not in request.GET:
        return TemplateResponse(
            request, "__async_data_feedback.html", {
                'functions': registered_functions
            }
        )

    params = {}
    # this is a bit of ugly magic to get single values instead of lists
    for k, v in request.GET.items():
        params[k] = request.GET.get(k)

    format = params.pop('data_format')
    function_name = params.pop('function_name')

    return data_to_response(format, function_name, **params)


def async_data_url(format, tagview_name, **params):
    """
    This is a template tag that returns back a valid url for async data
    """
    d = dict(data_format=format, function_name=tagview_name, **params)
    return reverse("async_data") + "?" + urlencode(d)


def djamix_debug(request):
    """
    This is a debug view
    """
    return TemplateResponse(request, "__debug.html", {
        'global_context': global_context,
        'tagviews': registered_functions,
        'models': djamix_models,
        'urlpatterns': urlpatterns,
    })


def extract_taggable_from_locals(defined_locals):
    """
    Local helper
    """
    afile = defined_locals['__file__']
    output = []
    for k, v in defined_locals.items():
        if (
            inspect.isfunction(v)
            and inspect.getfile(v) == afile
            and not v.__name__.startswith("_")
        ):
            output.append(v)

    return output


def urls_from_yaml(yaml_file_path):
    """
    Local helper
    """
    with open(yaml_file_path) as uf:
        views_description = yaml.load(uf)

    return views_description


def create_views_from_description(descriptions, global_context):
    """
    Takes list of dictionaries with descriptions and global context,
    returns urlpatterns with binded views
    """

    urlpatterns = []

    if not descriptions:
        # if no description given then provide some default view
        descriptions = [{
            'name': 'home',
            'path': '/',
            'template': DEFAULT_TEMPLATE_NAME,
        }]

    for v in descriptions:
        # wrapping because of python's late binding
        def make_function(v=v):

            def view(request, **kwargs):
                context = dict(global_context, **kwargs)
                context['querystring'] = dict(request.GET.items())
                return TemplateResponse(request, v['template'], context)

            return view

        function = make_function()
        v['function'] = function
        v['path_obj'] = path(v['path'].lstrip('/'), function, name=v['name'])
        urlpatterns.append(v['path_obj'])

    # at the end add the standard async and debug views
    urlpatterns += [
        path('__async_include__/', async_load,   name="async_include"),
        path('__async_data__/',    async_data,   name="async_data"),
        path('__djamix_debug__/',  djamix_debug, name="djamix_debug")
    ]

    urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)

    return urlpatterns


def handle_custom_user_commands(argv):
    """
    Super basic handle of custom user commands
    """
    # either runs the command and exits after the command is finished.
    # or just returns and then it fallbaacks to django command mechanism
    if argv[1] in USER_COMMANDS:
        print(USER_COMMANDS[argv[1]](*argv[2:]))
        exit()

    pass


def shell_command(defined_locals):
    return lambda: code.interact(local=defined_locals)


def start(paths=None, **settings_kwargs):
    """
    Main entry point for a djamix app
    """
    global urlpatterns
    global register
    global registered_functions
    global global_context
    global USER_COMMANDS
    global fake

    if 'LANGUAGE_CODE' in settings_kwargs:
        fake = Faker(settings_kwargs['LANGUAGE_CODE'])

    # don't pass locals explicitly
    frame = inspect.currentframe()
    defined_locals = frame.f_back.f_locals
    del frame

    settings.configure(
        DEBUG=True,
        SECRET_KEY='its not really secret',
        ROOT_URLCONF=__name__,
        MIDDLEWARE_CLASSES=[],
        INSTALLED_APPS=[
            'django.contrib.staticfiles',
            'django.contrib.humanize',
        ],
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': ['templates/'],
                'OPTIONS': {
                    # 'libraries': [],  -> for named templatetags
                    'builtins': [__name__],
                    'context_processors': [
                        'django.template.context_processors.debug',
                        'django.template.context_processors.request',
                    ],
                    'loaders': [
                        ('django.template.loaders.locmem.Loader', {
                            DEFAULT_TEMPLATE_NAME: DEFAULT_TEMPLATE_CONTENT,
                        }),
                        ('django.template.loaders.filesystem.Loader',
                         ['templates']),
                    ]
                },
            },
        ],
        STATIC_URL="/static/",
        STATICFILES_DIRS=['static_assets/'],
        MEDIA_URL=MEDIA_URL,
        MEDIA_ROOT=MEDIA_ROOT,
        USE_I18N=True,
        USE_L10N=True,
        USE_TZ=True,
        **settings_kwargs
    )

    _context = defined_locals.get('context', {})
    global_context = dict(global_context, **_context)
    # extend global context with all the models
    global_context = dict(global_context, **djamix_models)

    tags = extract_taggable_from_locals(defined_locals)
    paths_description = urls_from_yaml(paths) if paths else None
    # autoreload when urls are changed
    autoreload._cached_filenames.append(paths)

    urlpatterns = create_views_from_description(
        paths_description, global_context
    )

    for tag in tags:
        register.simple_tag(tag)
        register.filter(tag)
        registered_functions[tag.__name__] = tag
        USER_COMMANDS[tag.__name__] = tag

    for name, model in djamix_models.items():
        # add common things like .get and later .fake to the tags so we don't
        # have to write a function for every single case and could use
        # templatetags instead
        # import pdb; pdb.set_trace()
        register.simple_tag(
            lambda **x: model.objects.get(**x),
            name='%s.objects.get' % name
        )

        register.simple_tag(
            lambda x: model.objects.fake(x), name='%s.objects.fake' % name
        )

    USER_COMMANDS['shell'] = shell_command(defined_locals)

    register.simple_tag(media_url)
    register.simple_tag(async_include)
    register.simple_tag(async_data_url)

    handle_custom_user_commands(sys.argv)
    execute_from_command_line(sys.argv)


def rel(*x):
    """"Simple path helper"""
    abspath = os.path.abspath(__file__)
    BASE_DIR = os.path.dirname(abspath)
    return os.path.join(BASE_DIR, *x)


def create_project(project_name):
    """
    Copy a template project to the current directory
    """
    print("Creating new project... %s" % project_name)
    source = rel('project_template/')
    destination = os.path.join(os.getcwd(), project_name)
    shutil.copytree(source, destination)
    print(source, '=>', destination)


if __name__ == '__main__':

    if sys.argv[1] == 'create_project':
        create_project(sys.argv[2])

    else:
        print("Usage: djamix.py create_project <project_name>")
