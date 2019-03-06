import os
import threading

from turingarena.driver.language import Language
from turingarena.evaluation.evaluator import Evaluator
from turingarena.evaluation.events import EvaluationEventType

from turingarena_web.model.submission import Submission, SubmissionStatus


def evaluate_thread(problem, submission):
    evaluator = Evaluator(problem.path)
    submission_files = dict(
        source=submission.path
    )

    submission.set_status(SubmissionStatus.EVALUATING)
    for event in evaluator.evaluate(files=submission_files, redirect_stderr=True, log_level="WARNING"):
        submission.event(event_type=event.type, payload=event.payload)

    submission.event(event_type=EvaluationEventType.DATA, payload=dict(type="end"))
    submission.set_status(SubmissionStatus.EVALUATED)


def evaluate(current_user, problem, contest, submitted_file):

    ext = os.path.splitext(submitted_file["filename"])[1]

    language = Language.from_extension(ext)
    if language not in contest.languages:
        raise RuntimeError(f"Unsupported file extension {ext}: please select another file!")

    submission = Submission.new(current_user, problem, contest, submitted_file["filename"])

    os.makedirs(os.path.split(submission.path)[0], exist_ok=True)

    with open(submission.path, "w") as f:
        f.write(submitted_file["content"])

    threading.Thread(target=evaluate_thread, args=(problem, submission)).start()

    return submission
