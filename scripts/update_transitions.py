from git import Repo
from github import Auth
from github import Github
from github import GithubIntegration
from github import NamedUser
import sys

import bibtex_handler as bh
import git_localrepo_handler as glh
from TOKEN import TOKEN


class Transition:
    def __init__(self, issue, command):
        self.issue = issue
        assert command in ["yes", "no"]
        self.command = command


def main():
    auth = Auth.Token(TOKEN)
    g = Github(auth=auth)
    gh_repo = g.get_repo("aewag/physical-attack-collection")

    repo = Repo(".")
    if repo.is_dirty():
        print("Repository is dirty. Cannot continue.")
        exit()

    issues = gh_repo.get_issues(labels=["in-review"])
    transitions = list()

    for issue in issues:
        print(issue.title)
        for comment in issue.get_comments():
            if comment.user.login != "aewag":
                print(f"Unknown user {comment.user} commented in {issue.title}")
                continue
            command = comment._rawData["body"].lower()
            if command not in ["yes", "no"]:
                print(f"Unhandled comment {command} in {issue.title}")
                continue
            break
        else:
            print(f"No updates received for {issue.title}")
            continue
        transitions.append(Transition(issue, command))

    for transition in transitions:
        # Read bibtex files
        in_review = bh.read_bibtex(bh.IN_REVIEW_FP)
        in_scope = bh.read_bibtex(bh.IN_SCOPE_FP)
        not_in_scope = bh.read_bibtex(bh.NOT_IN_SCOPE_FP)
        # Retrieve bibtex entry of publication from in_review
        publication = [
            e for e in in_review.entries if e["ID"] == transition.issue.title
        ]
        assert len(publication) == 1
        publication = publication[0]
        # Remove transition from in_review
        in_review.entries = [e for e in in_review.entries if e != publication]
        # Transit publication
        scope = in_scope if command == "yes" else not_inscope
        scope.entries.append(publication)
        # Write bibtex files
        bh.write_bibtex(bh.IN_REVIEW_FP, in_review)
        bh.write_bibtex(bh.IN_SCOPE_FP, in_scope)
        bh.write_bibtex(bh.NOT_IN_SCOPE_FP, not_in_scope)
        # Commit, open pull-request and auto-merge
        decision = "in-scope" if command == "yes" else "not-in-scope"
        title = f"Move {publication['ID']} to {decision} #{transition.issue.number}"
        repo.heads.develop.checkout()
        repo.index.add([bh.IN_REVIEW_FP, bh.IN_SCOPE_FP, bh.NOT_IN_SCOPE_FP])
        repo.index.commit(title)
        repo.remote("origin").push()
        pr = gh_repo.create_pull(base="master", head="develop", title=title)
        pr.merge(merge_method="rebase")

        glh.cleanup_after_rebase_merge(repo)

        # Update issue
        labels = [decision]
        if command == "yes":
            labels.append("check-references")
        issue.edit(labels=labels)
        if command == "no":
            issue.edit(state="closed")


if __name__ == "__main__":
    sys.exit(main())
