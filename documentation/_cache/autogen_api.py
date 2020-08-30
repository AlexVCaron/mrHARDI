#!/usr/bin/env python
"""Script to auto-generate our API docs.
"""

import os
import sys

pjoin = os.path.join

here = os.path.abspath(os.path.dirname(__file__))
sys.path.append(pjoin(os.path.abspath(here), 'sphinxext'))

from apigen import ApiDocWriter

source = pjoin(here, 'source')

#*****************************************************************************
if __name__ == '__main__':
    package = 'magic_monkey'
    outdir = pjoin(source, 'api', 'generated')
    docwriter = ApiDocWriter(package, rst_extension='.rst')
    # You have to escape the . here because . is a special char for regexps.
    # You must do make clean if you change this!
    docwriter.package_skip_patterns += [r'\.external$',
                                        # Extensions are documented elsewhere.
                                        r'\.extensions',
                                        # This isn't API
                                        r'\.sphinxext',
                                        r'\.base',
                                        r'\.compute',
                                        r'\.setup'
                                        ]

    # The inputhook* modules often cause problems on import, such as trying to
    # load incompatible Qt bindings. It's easiest to leave them all out. The
    # main API is in the inputhook module, which is documented.
    docwriter.module_skip_patterns += []
    # Right now, all modules to exclude are skipped at package level

    # TODO : If this is unnecessary, remove
    # # These modules import functions and classes from other places to expose
    # # them as part of the public API. They must have __all__ defined. The
    # # non-API modules they import from should be excluded by the skip patterns
    # # above.
    # docwriter.names_from__all__.update({
    #     'IPython.display',
    # })
    
    # Now, generate the outputs
    docwriter.write_api_docs(outdir)
    # Write index with .txt extension - we can include it, but Sphinx won't try
    # to compile it
    docwriter.write_index(outdir, 'gen.txt',
                          relative_to=pjoin(source, 'api')
                          )
    print('%d files written' % len(docwriter.written_modules))
