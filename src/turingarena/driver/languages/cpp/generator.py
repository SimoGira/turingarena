from turingarena.driver.gen.generator import InterfaceCodeGen


class CppCodeGen(InterfaceCodeGen):
    def visit_Parameter(self, d):
        indirections = "*" * d.dimensions
        return f"int {indirections}{d.variable.name}"

    def visit_Interface(self, n):
        self.line("#include <cstdio>")
        self.line("#include <cstdlib>")
        self.line()
        for c in n.constants:
            self.visit(c)
            self.line()
        for m in n.methods:
            self.line(f"{self.visit(m)};")
            self.line()
        self.line("int main() {")
        with self.indent():
            self.visit(n.main)
        self.line("}")

    def visit_InterfaceTemplate(self, n):
        for c in n.constants:
            self.visit(c)
            self.line()
        for m in n.methods:
            if m.description:
                for l in m.description:
                    self.line(f"// {l}")
            self.line(f"{self.visit(m.prototype)} {{")
            with self.indent():
                self.visit(m.body)
            self.line(f"}}")

    def visit_Prototype(self, n):
        return_type = "int" if n.has_return_value else "void"
        value_parameters = [self.visit(p) for p in n.parameters]
        callback_parameters = [
            self.visit(callback)
            for callback in n.callbacks
        ]
        parameters = ", ".join(value_parameters + callback_parameters)
        return f"{return_type} {n.name}({parameters})"

    def visit_Constant(self, n):
        # TODO: remove static in template
        self.line(f"static const int {self.visit(n.variable)} = {self.visit(n.value)};")

    def visit_Comment(self, n):
        self.line(f"// {n.text}")

    def visit_VariableDeclaration(self, n):
        pointers = "*" * n.dimensions
        self.line(f"static int {pointers}{n.variable.name};")

    def visit_Alloc(self, n):
        reference = self.visit(n.reference)
        dimensions = "*" * n.dimensions
        size = self.visit(n.size)
        self.line(f"{reference} = new int{dimensions}[{size}];")

    def visit_Callback(self, n):
        params = ", ".join(self.visit(p) for p in n.prototype.parameters)
        if n.prototype.has_return_value:
            return_value = " -> int"
        else:
            return_value = ""

        with self.collect_lines() as c:
            self.line(f"[]({params}){return_value}" " {")
            with self.indent():
                self.visit(n.body)
            self.line("}")
        return c.as_inline()

    def visit_Call(self, n):
        method = n.method

        value_arguments = [self.visit(p) for p in n.arguments]
        callback_arguments = [self.visit(c) for c in n.callbacks]

        parameters = ", ".join(value_arguments + callback_arguments)
        if method.has_return_value:
            return_value = f"{self.visit(n.return_value)} = "
        else:
            return_value = ""

        self.line(f"{return_value}{method.name}({parameters});")

    def visit_Print(self, write_statement):
        format_string = " ".join("%d" for _ in write_statement.arguments) + r"\n"
        args = ", ".join(self.visit(v) for v in write_statement.arguments)
        self.line(f"""printf("{format_string}", {args});""")

    def visit_Read(self, n):
        format_string = "".join("%d" for _ in n.arguments)
        scanf_args = ", ".join("&" + self.visit(v) for v in n.arguments)
        self.line(f"""scanf("{format_string}", {scanf_args});""")

    def visit_If(self, n):
        condition = self.visit(n.condition)
        headers = [
            f"if ({condition}) {{",
            f"}} else {{",
        ]
        for header, body in zip(headers, n.branches):
            if body is not None:
                self.line(header)
                with self.indent():
                    self.visit(body)
        self.line("}")

    def visit_For(self, s):
        index_name = s.index.variable.name
        size = self.visit(s.index.range)
        self.line(f"for (int {index_name} = 0; {index_name} < {size}; {index_name}++)" " {")
        with self.indent():
            self.visit(s.body)
        self.line("}")

    def visit_Loop(self, n):
        self.line("while (true) {")
        with self.indent():
            self.visit(n.body)
        self.line("}")

    def visit_Switch(self, n):
        for i, case in enumerate(n.cases):
            condition = " || ".join(
                f"{self.visit(n.value)} == {self.visit(label)}"
                for label in case.labels
            )
            if i == 0:
                self.line(f"if ({condition}) {{")
            else:
                self.line(f"}} else if ({condition}) {{")
            with self.indent():
                self.visit(case.body)
        self.line("}")

    def visit_Exit(self, n):
        self.line("exit(0);")

    def visit_Return(self, n):
        self.line(f"return {self.visit(n.value)};")

    def visit_Break(self, n):
        self.line("break;")

    def visit_Flush(self, n):
        self.line("fflush(stdout);")
