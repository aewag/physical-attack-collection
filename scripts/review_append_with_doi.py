import argparse
import bibtexparser
import calendar
from git import Repo
from github import Auth
from github import Github
from github import GithubIntegration
from itertools import chain
import json
import os
import string
import sys
import time
import urllib.request

import git_localrepo_handler as glh
from TOKEN import TOKEN


IN_REVIEW_FP = "bib/in-review.bib"
NOT_IN_SCOPE_FP = "bib/not-in-scope.bib"
IN_SCOPE_FP = "bib/in-scope.bib"
LITERATURE_FP = "bib/literature.bib"

API_CROSSREF = "https://api.crossref.org/works/"
API_CROSSREF_BIBTEX = "/transform/application/x-bibtex"

MAX_REFS = 50


def get_bibtex_with_doi(doi):
    try:
        with urllib.request.urlopen(
            f"{API_CROSSREF}{doi}{API_CROSSREF_BIBTEX}"
        ) as response:
            bibtex = response.read().decode()
        return bibtex
    except urllib.error.HTTPError:
        return None


def add_publication_to_bibtex(bibtex, publication):
    merged_ids = [
        e["ID"]
        for e in chain(
            read_bibtex(IN_REVIEW_FP).entries,
            read_bibtex(NOT_IN_SCOPE_FP).entries,
            read_bibtex(IN_SCOPE_FP).entries,
            read_bibtex(LITERATURE_FP).entries,
        )
    ]
    suffixes = [""]
    suffixes.extend(list(string.ascii_lowercase))
    for suffix in suffixes:
        if f"{publication['ID']}{suffix}" in merged_ids:
            continue
        break
    else:
        assert False, "I could not find any untaken suffix"
    publication["ID"] = f"{publication['ID']}{suffix}"
    bibtex.entries.append(publication)
    return bibtex


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
    parser.add_argument("doi", type=str, nargs="+")
    args = parser.parse_args(raw_args)
    assert len(args.doi) <= MAX_REFS, f"At most {MAX_REFS} references at once."

    repo = Repo(".")
    if repo.is_dirty():
        print("Repository is dirty. Cannot continue.")
        exit()
    repo.heads.develop.checkout()

    auth = Auth.Token(TOKEN)
    g = Github(auth=auth)
    rate_limit = g.get_rate_limit().core
    if rate_limit.remaining == 0:
        reset_timestamp = calendar.timegm(rate_limit.reset.timetuple())
        sleep_time = reset_timestamp - calendar.timegm(time.gmtime()) + 5
        if sleep_time > 0:
            print(f"GH rate-limit exceeded for {sleep_time}s")
            time.sleep(sleep_time)
            print("Woken up, let's continue")
    gh_repo = g.get_repo("aewag/physical-attack-collection")

    known_dois = []
    for fp in [IN_REVIEW_FP, NOT_IN_SCOPE_FP, IN_SCOPE_FP, LITERATURE_FP]:
        known_dois.extend([e["doi"].lower() for e in read_bibtex(fp).entries])
    for idx, doi in enumerate(args.doi):
        args.doi[idx] = None if doi.lower() in known_dois else doi
    unfiltered_dois = len(args.doi)
    args.doi = [doi for doi in args.doi if doi is not None]
    print(f"{len(args.doi)} of {unfiltered_dois} DOIs are yet unknown.")
    if not args.doi:
        return os.EX_OK

    for doi in args.doi:
        bibtex = get_bibtex_with_doi(doi)
        if bibtex is None:
            print(f"Didnot find bibtex for DOI = {doi}")
            continue
        publication = bibtexparser.loads(bibtex)
        if publication.entries == []:
            print(f"Bibtex parsing failed for DOI = {doi}")
            continue
        publication_text = bibtexparser.dumps(publication)
        publication = publication.entries[0]

        review = read_bibtex(IN_REVIEW_FP)
        review = add_publication_to_bibtex(review, publication)
        write_bibtex(IN_REVIEW_FP, review)

        # Github open new issue to track progress
        body = f"WDYT? Is this publication in scope?\n```\n{publication_text}```\nURL: {publication['url']}\nGoogle Scholar: https://scholar.google.de/scholar?hl=en&q={publication['doi']}"
        issue = gh_repo.create_issue(
            title=publication["ID"], body=body, labels=["in-review"]
        )
        # Commit, open pull-request and auto-merge
        title = f"in-review: Add {publication['ID']} #{issue.number}"
        repo.index.add([IN_REVIEW_FP])
        repo.index.commit(title)
        print(f"Added {publication['ID']} to in-review")
    repo.remote("origin").push()
    pr = gh_repo.create_pull(
        base="master", head="develop", title="Adding publications to review"
    )
    pr.merge(merge_method="rebase")

    glh.cleanup_after_rebase_merge(repo)
    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
