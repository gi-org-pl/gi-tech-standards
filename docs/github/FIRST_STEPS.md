
# Git & Github: First steps

## How to start?

The first step is to install Git and clone (download) the repository. You can download Git from here in the version
for your favorite operating system. You can also use the GitHub Desktop application, which offers a graphical
interface. In this document, we will focus on the console usage of Git.

**Note**: all our projects are well tested both on *Ubuntu 24.x.x* and *macOS Tahoe*. Some team members were also
using *Windows* for development, however it was very problematic. Use other platforms only for your own responsibility.

To enhance security, we require you to configure your local development environment in the way we can recognise your
identity. Please set up local `git` to add metadata on each push. There are two ways to achieve that.

1. shell

```shell
# replace <your name and surname> with your real name
git config --global user.name "<your name and surname>"

# replace <your email> with your real email that ends on @gi.org.pl
# if you don't have that email, contact administrator
git config --global user.email "<your email>"

# we usually recommend to sign off commits with SSH key you already have in your system
git config --global gpg.format ssh

# replace <path to your ssh key> with your real SSH public key
# example: ~/.ssh/id_ed25519.pub
git config --global user.signingkey <path to your ssh key>

# sign every commit
git config --global commit.gpgsign true
```

You need to repeat these steps on each new machine you'll be using for development. Wchich you may find to be quite annoying, instead, you may also
set up git via config files located either in ~/.gitconfig or ~/.config/git/config
here is an example:

1. config

```toml
[user]
    name = your-name
    email = youremail@email.com
    signingkey = <path to your ssh key>
[push]
    autoSetupRemote = true
    default = current 
[pull]
    rebase = true
[gpg]
    format = ssh
[commit]
    gpgsign = true
```

Further Reading/Reference: <https://git-scm.com/book/en/v2/Customizing-Git-Git-Configuration>

>[!Note]
>It is generally a good practice to keep such config files in a github repo.

**Pull requests containing unsigned commits will not be possible to merge.**

On the GitHub platform we require two additional security steps:

- add your organization email address (ending with **@gi.org.pl**) to your account
  (you can do it [in GitHub emails settings](https://github.com/settings/emails)),
- enable 2-factor authorization in your **GitHub** account
  (you manage it [in GitHub security settings](https://github.com/settings/security)),
- add your real name to your **GitHub** profile

These steps are allowing us to control exactly who is introducing the new changes into our repositories, thank you for
staying compliant with these rules.

## How to set up a repository?

Navigate to the directory in which you want to place your project. Let’s compare two commands:

```shell
git clone [repo]
git clone [repo] .
```

Replace `[repo]` with the link to the repository. The difference between these two commands is the dot at the end. If
there is no dot: Git will create a new folder with a name matching that of the repository and place all the files
there. If the dot is present: Git will clone the repository into the current directory. You can also use `git clone
[repo] [directory-name]` to automatically create a directory with given name and clone repository into this directory.

## How to save a change?

Let's talk about how working with Git looks. The basic unit of work is a commit, which is a single change in the code
that, however, can involve more than one file. For example, when we rename a class, we probably want to maintain
consistency across various files, so we introduce changes in several files within a single commit. So, how do we
commit?

We can distinguish four stages where the code may reside:

- Working directory – the changes made within the local copy of the repository,
- Staging area – the changes prepared for commit, the changes we want to include in the commit,
- Local repository – the changes that have been committed locally but are not yet synchronized with the cloud, and
therefore no one besides you sees them,
- Cloud repository – the changes synchronized in cloud.

All modifications to files occur in the working directory. These changes are marked in red when you run the command
`git status`. This command also reminds us that to add items to the staging area, we use the command
`git add [relative path to file]`. You can also add an entire directory with `git add [relative path to directory]` or
all changes in the current directory and its subdirectories with `git add .`. If you decide that you do not want to
commit a particular file after adding it to staging area, you can use the command `git restore --staged [file]` (this
also works for folders). Meanwhile, the command `git restore [file]` is used to undo all changes in the working
directory (for example, if you accidentally deleted an entire file — `git restore [file]` will restore it to the
version from the last commit).

Once we have our changes in the staging area and we want to "save" them in the repository, it is time to commit. It's
as simple as:

```shell
git commit -m [note: what has been done? / commit title]
```

If you run the command without the -m option, you might need to seek help with Google under the term "vim", because
you'll probably end up with vim editor opened. Basic notes: use I to enter typing mode, use escape to exit typing
mode, use :q! to force exit without saving and use :wq to save and exit.

After making a commit, we should synchronize it with the cloud. To do this, we use the command: `git push origin HEAD`.

## How to and why work with branches?

Before you start working, you need to create a local branch. All changes are made on separate code branches. Just like
leaves on a tree, changes on different branches of the repository are completely independent. This helps us avoid
conflicts. To create a new branch, use `git branch [new-branch-name]`.  To switch between branches, use
`git checkout [target-branch-name]`. You can also use `git checkout -b [target-branch-name]` to combine those two operations.

**Warning**: in most cases you have to checkout to `main`, use `git fetch` and `git pull` to refresh the main, and then
you should create a new branch. That's because branches are created relatively to your current state and you almost always
want to create branches on the top of the newest `main`. These commands will be described in a moment.

The ideal workflow is as follows: you are on `main`, create a new branch, perform the task, commit, and push. Then, in
the Pull Requests tab on the repository page, you will have the option to create a pull request. We use pull requests
to verify what goes into the final product. A pull request is a "request" to merge the changes from your branch into
the main branch. At this stage, our developers will review the code, possibly indicate what needs to be improved, and
only after their approval is it possible to merge your code.

*What after a successful merge? How to update the local repository?*
When a change is merged into the `main` branch, Git will not automatically download the changes for every user. This
is an intentional solution — when we are testing on a fixed version of the software, such surreptitious actions by Git
could cause confusion.

To update the local repository, i.e., the local main branch, you must be on it (`git checkout main`), and then run two
commands:

```shell
git fetch
git pull
```

The first command fetches information about the changes that have occurred in the cloud (metadata). The second
command, on the other hand, pulls the latest version of all branches in the cloud.

But imagine the following situation: you are working on a task, but your colleague needs to create a new component for
you. Your colleague created the component and managed to merge it into main. How do you make sure that this code also
appears in your task branch? Such a situation, where our base branch is updated and we want to incorporate this
update, is called a rebase. It works like this:

```shell
git checkout main
git fetch
git pull
git checkout my-branch
git rebase main
```

This way, we ensure that our changes are based on the latest version of the code from main.

## Other important commands

The `git status` command, which we only briefly discussed, is often indispensable. The tutorial will likely be
expanded as problems arise — for now, that’s all.
