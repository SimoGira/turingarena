import logging
from collections import OrderedDict

from turingarena.common import ImmutableObject, TupleLikeObject
from turingarena.protocol.driver.frames import Phase
from turingarena.protocol.exceptions import ProtocolExit
from turingarena.protocol.model.body import Body
from turingarena.protocol.model.scope import Scope
from turingarena.protocol.parser import parse_protocol

logger = logging.getLogger(__name__)


class InterfaceSignature(TupleLikeObject):
    __slots__ = ["variables", "functions", "callbacks"]


class InterfaceDefinition(ImmutableObject):
    __slots__ = ["signature", "body", "source_text", "ast"]

    @staticmethod
    def compile(source_text, **kwargs):
        ast = parse_protocol(source_text, **kwargs)

        scope = Scope()
        body = Body.compile(ast.body, scope=scope)
        signature = InterfaceSignature(
            variables=OrderedDict(body.scope.variables.items()),
            functions={
                c.name: c.signature
                for c in body.scope.functions.values()
            },
            callbacks={
                c.name: c.signature
                for c in body.scope.callbacks.values()
            },
        )
        return InterfaceDefinition(
            source_text=source_text,
            ast=ast,
            signature=signature,
            body=body,
        )

    def run(self, context):
        main = self.body.scope.main["main"]

        logger.debug(f"running main")

        if context.phase is Phase.PREFLIGHT:
            request = context.engine.process_request(expected_type="main_begin")
            for variable, value in zip(self.signature.variables.values(), request.global_variables):
                context.engine.root_frame[variable] = value

        try:
            yield from main.body.run(context)
        except ProtocolExit:
            logger.debug(f"exit was reached")
            if context.phase is Phase.PREFLIGHT:
                context.engine.process_request(expected_type="exit")
        else:
            logger.debug(f"main body reached end")
            if context.phase is Phase.PREFLIGHT:
                context.engine.process_request(expected_type="main_end")

        # end of last communication block
        if context.phase is Phase.PREFLIGHT:
            context.engine.flush()
        if context.phase is Phase.RUN:
            yield
