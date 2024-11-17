import argparse
import bibtexparser
from git import Repo
from github import Auth
from github import Github
from github import GithubIntegration
from itertools import chain
import json
import os
import sys
import urllib.request

import git_localrepo_handler as glh
from TOKEN import TOKEN


IN_REVIEW_FP = "bib/in-review.bib"
NOT_IN_SCOPE_FP = "bib/not-in-scope.bib"
IN_SCOPE_FP = "bib/in-scope.bib"
LITERATURE_FP = "bib/literature.bib"

API_CROSSREF = "https://api.crossref.org/works/"
API_CROSSREF_BIBTEX = "/transform/application/x-bibtex"


def get_bibtex_with_doi(doi):
    try:
        with urllib.request.urlopen(
            f"{API_CROSSREF}{doi}{API_CROSSREF_BIBTEX}"
        ) as response:
            bibtex = response.read().decode()
        return bibtex
    except urllib.error.HTTPError:
        return None


def read_bibtex(fp):
    with open(fp, "r") as file:
        bibtex = file.read()
    return bibtexparser.loads(bibtex)


def write_bibtex(fp, bibtex):
    bibtex = bibtexparser.dumps(bibtex)
    with open(fp, "w") as file:
        file.write(bibtex)


def main(raw_args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("doi", type=str)
    args = parser.parse_args(raw_args)

    repo = Repo(".")
    if repo.is_dirty():
        print("Repository is dirty. Cannot continue.")
        exit()

    for fp in [IN_REVIEW_FP, NOT_IN_SCOPE_FP, IN_SCOPE_FP, LITERATURE_FP]:
        if args.doi.lower() in [e["doi"].lower() for e in read_bibtex(fp).entries]:
            print("Publication is already contained in one of the bib files")
            return os.EX_OK

    bibtex = get_bibtex_with_doi(args.doi)
    if bibtex is None:
        print(f"Didnot find bibtex for DOI = {args.doi}")
        return os.EX_DATAERR
    publication = bibtexparser.loads(bibtex)
    publication_text = bibtexparser.dumps(publication)
    publication = publication.entries[0]

    review = read_bibtex(IN_REVIEW_FP)
    review.entries.append(publication)
    write_bibtex(IN_REVIEW_FP, review)

    # Github open new issue to track progress
    auth = Auth.Token(TOKEN)
    g = Github(auth=auth)
    gh_repo = g.get_repo("aewag/physical-attack-collection")
    body = f"WDYT? Is this publication in scope?\n```\n{publication_text}```\nURL: {publication['url']}\nGoogle Scholar: https://scholar.google.de/scholar?hl=en&q={publication['doi']}"
    issue = gh_repo.create_issue(
        title=publication["ID"], body=body, labels=["in-review"]
    )
    # Commit, open pull-request and auto-merge
    title = f"in-review: Add {publication['ID']} #{issue.number}"
    repo.heads.develop.checkout()
    repo.index.add([IN_REVIEW_FP])
    repo.index.commit(title)
    repo.remote("origin").push()
    pr = gh_repo.create_pull(base="master", head="develop", title=title)
    pr.merge(merge_method="rebase")

    glh.cleanup_after_rebase_merge(repo)
    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
