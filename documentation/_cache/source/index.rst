.. _introduction:

==========================
mrHARDI Documentation
==========================

.. only:: html

   :Release: This will have to be \|release\| when we have it
   :Date: |today|

Welcome to mrHARDI, a modular, parallel and configurable magnetic
resonance image processing and analysis toolbox, based on some of the most
popular libraries available to date. The goal of this library is to facilitate
and humanize the implementation of complex data analysis pipelines. To do so,
the project is split into 3 part :

- An extensive and verbose command-line application used to test and configure
  calls to the various algorithms and dependencies used to process the images

- A collection of mri processing oriented functions and workflows, organized
  into modules which can be used to create efficient and complex pipelines.
  This is done all thanks to *Nextflow DSL 2*, a recent version of the
  powerful pipelining tool.

- A configuration toolbox, integrated both into the command-line application
  and the Nextflow modules, facilitating the prototyping and testing of new
  pipelines

You can find the table of content for this documentation in the left
sidebar, allowing you to come back to previous sections or skip ahead, if
needed.


.. toctree::
   :maxdepth: 1
   :hidden:

   self
   config/index
   api/index


.. only:: html

   * :ref:`genindex`
   * :ref:`modindex`
   * :ref:`search`

