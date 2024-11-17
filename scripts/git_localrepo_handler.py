def cleanup_after_rebase_merge(repo):
    repo.heads.master.checkout()
    repo.remote("origin").pull()
    repo.heads.develop.checkout()
    repo.git.rebase("origin/master")
    repo.remote("origin").push(force=True)
    repo.heads.master.checkout()
