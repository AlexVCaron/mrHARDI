mrHARDI Documentation
--------------------------

This directory contains the majority of the documentation for mrHARDI. It
is a fork of the documentation script from IPython, since the whole
application stack is built on traitlets (from IPython).


Requirements
------------

The documentation must be built using Python 3.

In additions to :ref:`devinstall`,
the following tools are needed to build the documentation:

 - sphinx
 - sphinx_rtd_theme
 - docrepr

In a Python 3 ``venv``, you should be able to run::

 cd mrHARDI
 pip3 install -U -r docs/requirements.txt


Build Commands
--------------

The documentation gets built using ``make``, and comes in several flavors.

``make html`` - build the API and narrative documentation web pages, this is
the default ``make`` target, so running just ``make`` is equivalent to ``make
html``.

``make html_noapi`` - same as above, but without running the auto-generated API
docs. When you are working on the narrative documentation, the most time
consuming portion  of the build process is the processing and rending of the
API documentation. This build target skips that.

``make pdf`` will compile a pdf from the documentation.

You can run ``make help`` to see information on all possible make targets.

To save time,
the make targets above only process the files that have been changed since the
previous docs build.
To remove the previous docs build you can use ``make clean``.
You can also combine ``clean`` with other `make` commands;
for example,
``make clean html`` will do a complete rebuild of the docs or `make clean pdf`
will do a complete build of the pdf.
