# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

sys.path.insert(0, os.path.abspath('../../'))

# -- Project information -----------------------------------------------------

project = 'CLEAVE'
copyright = '2020, KTH Royal Institute of Technology'
author = 'ExPECA Project Team'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinxcontrib.napoleon',
    'm2r2'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# source_suffix = '.rst'
source_suffix = ['.rst', '.md']

# index.rst is the master document
master_doc = 'index'

# autodoc rules
autodoc_default_options = {
    # 'members'        : 'var1, var2',
    'member-order'   : 'bysource',
    'special-members': 'yes',
    'undoc-members'  : 'yes',
    'exclude-members': '__weakref__, __abstractmethods__, __dict__, '
                       '__module__, __doc__, __init__'
}
autoclass_content = 'both'


def autodoc_skip_member(app, what, name, obj, skip, options):
    exclusions = ('__weakref__',  # special-members
                  '__doc__',
                  '__module__',
                  '__dict__',  # undoc-members
                  'setup.py'
                  )
    exclude = name in exclusions
    return skip or exclude


def setup(app):
    app.connect('autodoc-skip-member', autodoc_skip_member)
