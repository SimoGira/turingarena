import logging
from contextlib import ExitStack, contextmanager
from functools import lru_cache
from tempfile import TemporaryDirectory

from turingarena_impl.algorithm import Algorithm
from turingarena_impl.interface.interface import InterfaceDefinition
from turingarena_impl.metaserver import MetaServer
from turingarena_impl.pipeboundary import PipeBoundarySide, PipeBoundary
from turingarena_impl.sandbox.connection import SandboxProcessConnection, SANDBOX_PROCESS_CHANNEL, \
    SANDBOX_QUEUE, SANDBOX_REQUEST_QUEUE
from turingarena_impl.sandbox.languages.language import Language
from turingarena_impl.sandbox.process import CompilationFailedProcess
from turingarena_impl.sandbox.source import AlgorithmSource, CompilationFailed

logger = logging.getLogger(__name__)


class SandboxException(Exception):
    pass


class SandboxServer(MetaServer):
    def get_queue_descriptor(self):
        return SANDBOX_QUEUE

    @contextmanager
    def run_child_server(self, child_server_dir, *, language_name, source_name, interface_name):
        algorithm = Algorithm(language_name=language_name, source_name=source_name, interface_name=interface_name)
        server = SandboxProcessServer(
            algorithm=algorithm,
            sandbox_dir=child_server_dir,
            meta_server=self,
        )
        yield
        server.run()

    def create_response(self, child_server_dir):
        return dict(sandbox_process_dir=child_server_dir)

    @lru_cache(maxsize=None)
    def compile_algorithm(self, algorithm):
        language = Language.from_name(algorithm.language_name)
        interface = InterfaceDefinition.load(algorithm.interface_name)
        source = AlgorithmSource.load(
            algorithm.source_name,
            interface=interface,
            language=language,
        )
        try:
            with ExitStack() as exit:
                compilation_dir = exit.enter_context(TemporaryDirectory(prefix="turingarena_"))
                source.compile(compilation_dir)
                # if everything went ok, keep the temporary dir until we stop
                self.exit_stack.push(exit.pop_all())
        except CompilationFailed:
            return source, None
        else:
            return source, compilation_dir


class SandboxProcessServer:
    def __init__(self, *, sandbox_dir, algorithm, meta_server):
        self.algorithm = algorithm
        self.meta_server = meta_server

        self.boundary = PipeBoundary(sandbox_dir)
        self.boundary.create_channel(SANDBOX_PROCESS_CHANNEL)
        self.boundary.create_queue(SANDBOX_REQUEST_QUEUE)

        self.done = False
        self.process = None

        self.process_exit_stack = ExitStack()

    def run(self):
        logger.debug("starting process...")

        with self.boundary.open_channel(SANDBOX_PROCESS_CHANNEL, PipeBoundarySide.SERVER) as pipes:
            source, compilation_dir = self.meta_server.compile_algorithm(self.algorithm)
            connection = SandboxProcessConnection(**pipes)
            if compilation_dir:
                self.process = self.process_exit_stack.enter_context(
                    source.run(compilation_dir, connection)
                )
            else:
                self.process = CompilationFailedProcess()

        logger.debug("process started")

        while not self.done:
            logger.debug("handling requests...")
            self.boundary.handle_request(
                SANDBOX_REQUEST_QUEUE,
                self.handle_request,
            )

        logger.debug("process terminated")

    def handle_request(self, *, wait):
        logger.debug(f"get_info(wait={wait})")

        assert not self.done
        assert wait in ("0", "1")

        info = self.process.get_status(wait_termination=bool(int(wait)))

        time_usage = info.time_usage
        memory_usage = info.memory_usage
        logger.debug(f"Process info = {info}")

        if wait == "1":
            self.done = True
            self.process = None

        return {
            "error": info.error,
            "time_usage": str(time_usage),
            "memory_usage": str(memory_usage),
        }
