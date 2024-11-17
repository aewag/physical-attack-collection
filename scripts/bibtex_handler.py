import bibtexparser
import json
import urllib.request

IN_REVIEW_FP = "bib/in-review.bib"
NOT_IN_SCOPE_FP = "bib/not-in-scope.bib"
IN_SCOPE_FP = "bib/in-scope.bib"
LITERATURE_FP = "bib/literature.bib"

API_CROSSREF = "https://api.crossref.org/works/"
API_CROSSREF_BIBTEX = "/transform/application/x-bibtex"


def get_bibtex_with_doi(doi):
    with urllib.request.urlopen(
        f"{API_CROSSREF}{doi}{API_CROSSREF_BIBTEX}"
    ) as response:
        bibtex = response.read().decode()
    return bibtex


def read_bibtex(fp):
    with open(fp, "r") as file:
        bibtex = file.read()
    return bibtexparser.loads(bibtex)


def write_bibtex(fp, bibtex):
    bibtex = bibtexparser.dumps(bibtex)
    with open(fp, "w") as file:
        file.write(bibtex)
