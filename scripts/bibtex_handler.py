import bibtexparser
import json
import urllib.request

IN_REVIEW_FP = "bib/in-review.bib"
NOT_IN_SCOPE_FP = "bib/not-in-scope.bib"
IN_SCOPE_FP = "bib/in-scope.bib"
UNKNOWN_FP = "bib/unknown.json"
LITERATURE_FP = "bib/literature.bib"

API_CROSSREF = "https://api.crossref.org/works/"
API_CROSSREF_BIBTEX = "/transform/application/x-bibtex"

API_SEMANTICSCHOLAR = "https://api.semanticscholar.org/v1/paper/"
API_SEMANTICSCHOLAR_SUFFIX = "?include_unknown_references=true"


def get_bibtex_with_doi(doi):
    with urllib.request.urlopen(
        f"{API_CROSSREF}{doi}{API_CROSSREF_BIBTEX}"
    ) as response:
        bibtex = response.read().decode()
    return bibtex


def get_references_with_doi(doi):
    references = list()
    # crossref
    with urllib.request.urlopen(f"{API_CROSSREF}{doi}") as response:
        dct = json.load(response)
    msg = dct["message"]
    references.extend(msg.get("reference", []))
    # semanticscholar
    try:
        with urllib.request.urlopen(
            f"{API_SEMANTICSCHOLAR}{doi}{API_SEMANTICSCHOLAR_SUFFIX}"
        ) as response:
            dct = json.load(response)
        references.extend(dct.get("references", []))
        references.extend(dct.get("citations", []))
    except urllib.error.HTTPError as err:
        print(f"s2 {doi} - {err}")
    return references


def read_bibtex(fp):
    with open(fp, "r") as file:
        bibtex = file.read()
    return bibtexparser.loads(bibtex)


def write_bibtex(fp, bibtex):
    bibtex = bibtexparser.dumps(bibtex)
    with open(fp, "w") as file:
        file.write(bibtex)


def update_unknown(unknown_unhandled):
    with open(UNKNOWN_FP, "r") as file:
        unknown = file.read()
    unknown = json.loads(unknown) if unknown else {"unhandled": [], "handled": []}
    unknown["unhandled"].extend(unknown_unhandled)
    with open(UNKNOWN_FP, "w") as file:
        file.write(json.dumps(unknown, indent=4))
