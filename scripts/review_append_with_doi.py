import argparse
import bibtexparser
from git import Repo
from github import Auth
from github import Github
from github import GithubIntegration
from itertools import chain
import json
import sys
import urllib.request

from TOKEN import TOKEN


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("doi", type=str)
    args = parser.parse_args()

    repo = Repo(".")
    if repo.is_dirty():
        print("Repository is dirty. Cannot continue.")
        exit()
    repo.heads.develop.checkout()

    for fp in [IN_REVIEW_FP, NOT_IN_SCOPE_FP, IN_SCOPE_FP, LITERATURE_FP]:
        if args.doi in [entry["doi"] for entry in read_bibtex(fp).entries]:
            print("Publication is already contained in one of the bib files")
            exit()

    bibtex = get_bibtex_with_doi(args.doi)
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
    body = f"WDYT? Is this publication in scope?\n```\n{publication_text}```"
    issue = gh_repo.create_issue(
        title=publication["ID"], body=body, labels=["in-review"]
    )
    # Commit, open pull-request and auto-merge
    title = f"in-review: Add {publication['ID']} #{issue.number}"
    repo.index.add([IN_REVIEW_FP])
    repo.index.commit(title)
    repo.remote("origin").push()
    pr = gh_repo.create_pull(base="master", head="develop", title=title)
    pr.merge(merge_method="rebase")

    repo.heads.master.checkout()
    repo.remote("origin").pull()
    repo.heads.develop.checkout()
    repo.git.rebase("origin/master")
    repo.remote("origin").push(force=True)
    repo.heads.master.checkout()


if __name__ == "__main__":
    sys.exit(main())
