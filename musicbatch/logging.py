'''Logging setup'''


import logging
import os


package = __name__.split('.')[0]  # top-level package
log = logging.getLogger(package)

if not log.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    log.addHandler(handler)

if os.environ.get('DEBUG'):
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.WARNING)

del(handler)
del(package)
