from __future__ import print_function

import subprocess
import argparse
import logging
import json
import uuid
import sys
import os

try:
    from shlex import quote
except ImportError:
    from pipes import quote


from turingarena_cli.common import *


logger = logging.Logger("CLI")

ssh_cli = [
    "ssh",
    "-o", "BatchMode=yes",
    "-o", "LogLevel=error",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "StrictHostKeyChecking=no",
    "-p", "20122", "-q",
]

git_env = {}


def new_problem(name, language):
    if not language:
        language = "python"

    evaluators = {
        "python": "evaluator.py",
        "c++": "evaluator.cpp",
    }

    if language not in evaluators:
        error("Language {} not supported".format(language))
        return

    ok("Creating new problem {}".format(name))

    info("Making directory {}/".format(name))
    os.makedirs(name)
    os.chdir(name)

    info("Initializing empty git repository")
    subprocess.call(["git", "init", "--quiet"])

    info("Writing default interface.txt")
    with open("interface.txt", "w") as f:
        print("// put here your function and procedure definitions\n\n"
              "main {\n // put here the main code\n}", file=f)

    info("writing default {}".format(evaluators[language]))
    with open(evaluators[language], "w") as f:
        print("# Write here your evaluator code", file=f)

    ok("Problem created in directory {}/".format(name))


def build_json_parameters(args):
    return json.dumps(vars(args))


def local_command(args):
    cli = [
        "python3",
        "-m", "turingarena_impl.server_cli",
        build_json_parameters(args),
    ]

    subprocess.call(cli)


def send_ssh_command(cli):
    if sys.stdout.isatty():
        tty_allocation = "-t"
    else:
        tty_allocation = "-T"

    cli = ssh_cli + [
        tty_allocation,
        "turingarena@localhost",
    ] + cli

    logger.info("Sending command to the server via ssh")
    subprocess.call(cli)


def ssh_command(args):
    cli = [
        "/usr/local/bin/python",
        "-m", "turingarena_impl.server_cli",
        quote(build_json_parameters(args)),
    ]

    send_ssh_command(cli)


def setup_git_env():
    global git_env

    git_dir = os.path.join(os.path.expanduser("~"), ".turingarena", "db.git")

    try:
        working_dir = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            universal_newlines=True,
        ).strip()
    except:
        working_dir = os.getcwd()
        logger.info("Initializing git repository in {}".format(working_dir))
        subprocess.call(["git", "init"])

    author_name = "TuringArena"
    author_email = "contact@turingarena.org"

    git_env = {
        "GIT_WORK_TREE": working_dir,
        "GIT_DIR": git_dir,
        "GIT_SSH_COMMAND": " ".join("'" + c + "'" for c in ssh_cli),
        "GIT_AUTHOR_NAME": author_name,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_COMMITTER_NAME": author_name,
        "GIT_COMMITTER_EMAIL": author_email,
    }

    subprocess.check_call(["git", "init", "--quiet", "--bare", git_dir])
    logger.info("Initialized git repository in {}".format(git_dir))

    return git_dir


def send_current_dir(local):
    global git_env
    working_dir = git_env["GIT_WORK_TREE"]

    current_dir = os.path.relpath(os.curdir, working_dir)
    logger.info("Sending work dir: {working_dir} (current dir: {current_dir})...".format(
        working_dir=working_dir,
        current_dir=current_dir,
    ))

    git_popen_args = dict(env=git_env, universal_newlines=True)

    subprocess.check_call(["git", "add", "-A", "."], **git_popen_args)
    logger.info("Added all files to git")

    tree_id = subprocess.check_output(["git", "write-tree"], **git_popen_args).strip()
    logger.info("Wrote tree with id {}".format(tree_id))

    if not local:
        logger.info("Sending current directory to the server via git")

        commit_message = "Turingarena payload."
        commit_id = subprocess.check_output(
            ["git", "commit-tree", tree_id, "-m", commit_message],
            **git_popen_args
        ).strip()

        logger.info("Created commit {}".format(commit_id))

        subprocess.check_call(ssh_cli + [
            "turingarena@localhost",
            "git init --bare --quiet db.git",
        ])
        logger.info("Initialized git repository on the server")

        subprocess.check_call([
            "git", "push", "-q",
            "turingarena@localhost:db.git",
            "{commit_id}:refs/heads/sha-{commit_id}".format(commit_id=commit_id),
        ], **git_popen_args)
        logger.info("Pushed current commit")

        # remove the remove branch (we only need the tree object)
        subprocess.check_call([
            "git", "push", "-q",
            "turingarena@localhost:db.git",
            ":refs/heads/sha-{commit_id}".format(commit_id=commit_id),
        ], **git_popen_args)

    return current_dir, tree_id


def retrive_result(result_file):
    logger.info("Retriving result")
    info("Reading {}".format(result_file))
    with open(result_file) as f:
        result = f.read().strip()

    logger.info("Got {}".format(result))
    result = json.loads(result)

    tree_id = result["tree_id"]
    commid_it = result["commit_id"]

    logger.info("Importing tree id {}".format(tree_id))
    subprocess.call(["git", "read-tree", tree_id], env=git_env)
    logger.info("Checking out")
    subprocess.call(["git", "checkout-index", "--all", "-q"], env=git_env)


def create_evaluate_parser(evaluate_parser):
    evaluate_parser.add_argument("file", help="submission file", nargs="+")
    evaluate_parser.add_argument("--evaluator", "-e", help="command evaluator")
    evaluate_parser.add_argument("--raw", "-r", help="use raw output", action="store_true")


def create_make_parser(make_parser):
    make_parser.add_argument("what", help="what to make", default="all",
                             choices=["all", "skeleton", "template", "metadata", "description"])
    make_parser.add_argument("--language", "-l", help="which language to generate", action="append",
                             choices=["python", "c++", "java"])
    make_parser.add_argument("--print", "-p", help="Print output to stdout instead of writing it to a file", action="store_true")


def create_new_parser(new_parser):
    new_parser.add_argument("name", help="problem name")
    new_parser.add_argument("--language", "-l", help="language for the evaluator")


def create_info_parser(info_parser):
    info_parser.add_argument("what", choices=["languages"], help="list supported TuringArena arguments")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Turingarena CLI")
    parser.add_argument("--local", "-l", help="execute turingarena locally (do not connect to docker)",
                        action="store_true")
    parser.add_argument("--send-current-dir", "-s", help="send the current directory", action="store_true")
    parser.add_argument("--tree", "-t", help="a git tree id", action="append")
    parser.add_argument("--repository", "-r", help="source of a git repository", action="append")
    parser.add_argument("--log-level", help="log level", default="WARNING")

    subparsers = parser.add_subparsers(title="command", dest="command")
    subparsers.required = True

    make_parser = subparsers.add_parser("make", help="Generate all the necessary files for a problem")
    create_make_parser(make_parser)

    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate a submission")
    create_evaluate_parser(evaluate_parser)

    info_parser = subparsers.add_parser("info", help="get some info about TuringArena")
    create_info_parser(info_parser)

    new_parser = subparsers.add_parser("new", help="Create a new Turingarena problem")
    create_new_parser(new_parser)

    return parser.parse_args()


def main():
    args = parse_arguments()

    logger.setLevel(args.log_level)

    if args.command == "new":
        new_problem(args.name, args.language)
        return

    args.git_dir = setup_git_env()

    if args.command == "make" and args.what != "all":
        args.print = True

    if args.repository is None:
        args.send_current_dir = True

    if args.command not in ["evaluate", "make"]:
        args.send_current_dir = False

    if args.send_current_dir:
        args.current_dir, args.tree_id = send_current_dir(local=args.local)

    args.result_file = os.path.join("/tmp", "turingarena_{}_result.json".format(str(uuid.uuid4())))

    if args.local:
        local_command(args)
    else:
        ssh_command(args)

    if args.command == "make" and not args.print:
        retrive_result(args.result_file)


if __name__ == "__main__":
    main()