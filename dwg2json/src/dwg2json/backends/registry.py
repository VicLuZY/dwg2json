from .libredwg_backend import LibreDwgBackend

BACKENDS = {
    "auto": LibreDwgBackend,
    "libredwg": LibreDwgBackend,
}
