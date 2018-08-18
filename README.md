# djamix
Djamix source code

# What is djamix?

Djamix (django remix) is a library that aims to simplify the process of
creating mockups and prototypes based on django.

It does that by choosing a subset of django features that are most important
for prototyping, and making them much easier to use.

It's best to see some examples. :)


# Installation

`pip install djamix`

It depends on Django 2.x


# Examples

Create empty file, name it whatever you want (we'll use `manage.py` like in a
typical django project)

Import djamix and start it:

```
import djamix

djamix.start()
```

And now you can do all the regular django things with it, for example:

```
./manage.py version
./manage.py shell
./manage.py runserver
```

TBD.


# Running tests
Run `pytest` in the main directory, otherwise it will complain about paths to
fixtures used in tests.
