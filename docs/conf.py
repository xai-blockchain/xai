# Sphinx Configuration file for Blockchain Project Documentation

# -- Path setup --------------------------------------------------------------

import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

# -- Project information -----------------------------------------------------

project = 'Blockchain Project'
copyright = '2025, Blockchain Project Team'
author = 'Blockchain Project Team'

# The full version, including alpha/beta/rc tags
release = '1.0.0'
version = '1.0'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.ifconfig',
    'sphinx.ext.githubpages',
    'sphinx_rtd_theme',
]

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Autosummary settings
autosummary_generate = True
autosummary_imported_members = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
html_theme_options = {
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
    # Toc options
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# Add any paths that contain custom static files (such as style sheets)
html_static_path = ['_static']

# Custom sidebar templates
html_sidebars = {
    '**': [
        'globaltoc.html',
        'relations.html',
        'sourcelink.html',
        'searchbox.html',
    ]
}

# The name for this set of Sphinx documents.
html_title = f'{project} v{version} Documentation'

# A shorter title for the navigation bar.
html_short_title = project

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
# html_logo = None

# The name of an image file (within the static path) to use as favicon
# html_favicon = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'BlockchainProjectdoc'

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    'papersize': 'letterpaper',
    'pointsize': '10pt',
    'preamble': '',
    'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files.
latex_documents = [
    ('index', 'BlockchainProject.tex', 'Blockchain Project Documentation',
     'Blockchain Project Team', 'manual'),
]

# -- Options for manual page output ------------------------------------------

# One entry per manual page.
man_pages = [
    ('index', 'blockchainproject', 'Blockchain Project Documentation',
     [author], 1)
]

# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files.
texinfo_documents = [
    ('index', 'BlockchainProject', 'Blockchain Project Documentation',
     author, 'BlockchainProject', 'Blockchain project documentation.',
     'Miscellaneous'),
]

# -- Options for Epub output -------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# The unique identifier of the text.
# epub_identifier = ''

# A unique identification for the text.
# epub_uid = ''

# A list of files that should not be packed into the epub file.
epub_exclude_files = ['search.html']

# -- Extension configuration -------------------------------------------------

# Intersphinx configuration
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'requests': ('https://requests.readthedocs.io/en/latest/', None),
}

# Todo extension
todo_include_todos = True

# -- Custom configuration ----------------------------------------------------

# Source suffix
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# The master toctree document.
master_doc = 'index'

# Language for content autogenerated by Sphinx
language = 'en'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer.
html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer.
html_show_copyright = True

# If true, an OpenSearch description file will be output
html_use_opensearch = 'https://docs.blockchain-project.io'

# Output file base name for HTML help builder.
htmlhelp_basename = 'BlockchainProjectDoc'
