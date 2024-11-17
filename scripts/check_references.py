from git import Repo
from github import Auth
from github import Github
from github import GithubIntegration
from github import NamedUser
import sys

import bibtex_handler as bh
import git_localrepo_handler as glh
import review_append_with_doi
from TOKEN import TOKEN


def main():
    auth = Auth.Token(TOKEN)
    g = Github(auth=auth)
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
        no_doi_references = [r for r in references if "DOI" not in r]
        print(f"Following refernces have no DOI: {no_doi_references}")
        references = [r for r in references if "DOI" in r]
        for reference in references:
            review_append_with_doi.main([reference["DOI"]])
        labels = issue.get_labels()
        labels = [l for l in labels if l != "check-references"]
        issue.set_labels(labels)

if __name__ == "__main__":
    sys.exit(main())
