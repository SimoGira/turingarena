from bidict import bidict


def compile_statement(ast, *, scope):
    return get_statement_classes()[ast.statement_type].compile(ast, scope)


def get_statement_classes():
    from turingarena.interface.model.alloc import AllocStatement
    from turingarena.interface.model.calls import CallStatement, ReturnStatement
    from turingarena.interface.model.control import ForStatement, IfStatement, LoopStatement, ExitStatement
    from turingarena.interface.model.callables import FunctionStatement, CallbackStatement, MainStatement
    from turingarena.interface.model.variables import VarStatement
    from turingarena.interface.model.io import CheckpointStatement, InputStatement, OutputStatement, FlushStatement

    return bidict({
        "var": VarStatement,
        "function": FunctionStatement,
        "callback": CallbackStatement,
        "main": MainStatement,
        "alloc": AllocStatement,
        "checkpoint": CheckpointStatement,
        "input": InputStatement,
        "output": OutputStatement,
        "flush": FlushStatement,
        "call": CallStatement,
        "return": ReturnStatement,
        "exit": ExitStatement,
        "for": ForStatement,
        "if": IfStatement,
        "loop": LoopStatement,
    })