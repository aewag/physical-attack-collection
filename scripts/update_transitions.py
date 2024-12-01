import calendar
from git import Repo
from github import Auth
from github import Github
from github import GithubIntegration
from github import NamedUser
import time
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

    issues = gh_repo.get_issues(labels=["in-review"], sort="comments-desc")
    transitions = list()

    for issue in issues:
        comments = issue.get_comments()
        if comments.totalCount == 0:
            print("No more updates assumed, because of issues sorting")
            break
        for comment in comments:
            if comment.user.login != "aewag":
                print(f"Unknown user {comment.user} commented in {issue.title}")
                continue
            command = comment._rawData["body"].lower()
            if command not in ["yes", "no"]:
                print(f"Unhandled comment {command} in {issue.title}")
                continue
            print(f"Updates received for {issue.title}")
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
        scope = in_scope if transition.command == "yes" else not_in_scope
        scope.entries.append(publication)
        # Write bibtex files
        bh.write_bibtex(bh.IN_REVIEW_FP, in_review)
        bh.write_bibtex(bh.IN_SCOPE_FP, in_scope)
        bh.write_bibtex(bh.NOT_IN_SCOPE_FP, not_in_scope)
        # Commit and push
        decision = "in-scope" if transition.command == "yes" else "not-in-scope"
        title = f"Move {publication['ID']} to {decision} #{transition.issue.number}"
        repo.heads.develop.checkout()
        repo.index.add([bh.IN_REVIEW_FP, bh.IN_SCOPE_FP, bh.NOT_IN_SCOPE_FP])
        repo.index.commit(title)
        repo.remote("origin").push()

        # Update issue
        issue = transition.issue
        labels = issue.get_labels()
        labels = [l.name for l in labels if l.name != "in-review"]
        labels.append(decision)
        if transition.command == "yes":
            labels.append("check-references")
        issue.edit(labels=labels)
        if transition.command == "no":
            issue.edit(state="closed")

    pr = gh_repo.create_pull(base="master", head="develop", title=title)
    pr.merge(merge_method="rebase")

    glh.cleanup_after_rebase_merge(repo)


if __name__ == "__main__":
    sys.exit(main())
