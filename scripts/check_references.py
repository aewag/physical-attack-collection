import calendar
from git import Repo
from github import Auth
from github import Github
from github import GithubIntegration
from github import NamedUser
from github import RateLimit
import os
import json
import sys
import time

import bibtex_handler as bh
import git_localrepo_handler as glh
import review_append_with_doi
from TOKEN import TOKEN


def main():
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

    repo = Repo(".")
    if repo.is_dirty():
        print("Repository is dirty. Cannot continue.")
        exit()

    issues = gh_repo.get_issues(labels=["check-references"])
    in_scope = bh.read_bibtex(bh.IN_SCOPE_FP)

    for issue in issues:
        print(f"Checking references for issue {issue.title}")
        publication = [e for e in in_scope.entries if e["ID"] == issue.title]
        assert len(publication) == 1
        publication = publication[0]

        references = bh.get_references_with_doi(publication["doi"])
        unknown_references = [r for r in references if "doi" not in r and "DOI" not in r]

        references = [r for r in references if "doi" in r or "DOI" in r]
        print(f"Found {len(references)} references and citations for {issue.title})")
        for reference in references:
            doi = reference["DOI"] if "DOI" in reference else reference["doi"]
            if doi is not None:
                result = review_append_with_doi.main([doi])
                if result == os.EX_OK:
                    continue
            unknown_references.append(reference)

        bh.update_unknown(unknown_references)

        labels = issue.get_labels()
        labels = [l.name for l in labels if l.name != "check-references"]
        issue.edit(labels=labels)


if __name__ == "__main__":
    sys.exit(main())
