from turingarena.interface.model.node import AbstractSyntaxNode
from turingarena.interface.model.scope import Scope
from turingarena.interface.model.statement import ImperativeStatement
from turingarena.interface.model.statements import compile_statement


class Body(AbstractSyntaxNode):
    __slots__ = ["statements", "scope"]

    @staticmethod
    def compile(ast, *, scope):
        scope = Scope(scope)
        return Body(
            scope=scope,
            statements=[
                compile_statement(s, scope=scope)
                for s in ast.statements
            ]
        )

    def run(self, context):
        with context.enter(self.scope) as inner_context:
            for statement in self.statements:
                if isinstance(statement, ImperativeStatement):
                    yield from statement.run(inner_context)

    def is_possible_branch(self, *, context):
        request = context.engine.peek_request()
        if request.message_type == "function_call":
            call = request.function_name
        elif request.message_type == "exit":
            call = ExitCall
        else:
            call = None
        return call is not None and call in self.first_calls()

    def first_calls(self):
        ans = {None}
        for s in self.statements:
            if None not in ans:
                break
            ans.remove(None)
            ans.update(s.first_calls())
        return ans


ExitCall = object()