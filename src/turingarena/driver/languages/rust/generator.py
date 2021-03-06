from turingarena.driver.gen.generator import InterfaceCodeGen


read_macro = r"""
macro_rules! readln {
    ($($var:expr),*) => {{
        let mut buf = String::new();
        std::io::stdin().read_line(&mut buf).unwrap();
        let parts: Vec<&str> = buf.trim().split(" ").collect();
        let mut i: usize = 0;
        $(
            assert!(i < parts.len(), "input format incorrect: too few values on this line"); 
            $var = parts[i].parse().unwrap();
            i += 1;
        )*
        assert!(i == parts.len(), "input format incorrect: too many values on the line")
    }};
}
"""


class RustCodeGen(InterfaceCodeGen):
    @staticmethod
    def build_type(dimensions):
        if dimensions == 0:
            return "i64"
        else:
            return f"Vec<{RustCodeGen.build_type(dimensions - 1)}>"

    def build_callback(self, c):
        return_type = "-> i64" if c.has_return_value else ""
        args = ", ".join([
            self.build_type(arg.dimensions)
            for arg in c.parameters
        ])
        return f"{c.name}: fn({args}){return_type}"

    def visit_Parameter(self, d):
        return f"{d.variable.name}: {self.build_type(d.dimensions)}"

    def visit_Interface(self, n):
        self.line("mod solution;")
        self.line("use std::io::Write;")
        self.line(read_macro)
        for c in n.constants:
            self.visit(c)
        self.line()
        self.line("fn main() {")
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
            self.line(f"pub fn {self.visit(m.prototype)} {{")
            with self.indent():
                self.visit(m.body)
            self.line(f"}}")

    def visit_Subscript(self, e):
        return f"{self.visit(e.array)}[{self.visit(e.index)} as usize]"

    def visit_Prototype(self, n):
        return_type = "-> i64" if n.has_return_value else ""
        value_parameters = [self.visit(p) for p in n.parameters]
        callback_parameters = [
            self.build_callback(callback)
            for callback in n.callbacks
        ]
        parameters = ", ".join(value_parameters + callback_parameters)
        return f"{n.name}({parameters}) {return_type}"

    def visit_Constant(self, n):
        self.line(f"const {self.visit(n.variable)}: i64 = {self.visit(n.value)};")

    def visit_Comment(self, n):
        self.line(f"// {n.text}")

    def visit_VariableDeclaration(self, n):
        t = self.build_type(n.dimensions)
        init = " = Vec::new()" if n.dimensions > 0 else ""
        mut = "mut " if n.dimensions > 0 else ""
        self.line(f"let {mut}{n.variable.name}: {t}{init};")

    def visit_Alloc(self, n):
        t = "vec::new()" if n.dimensions > 0 else "0"
        reference = self.visit(n.reference)
        size = self.visit(n.size)
        self.line(f"{reference}.resize({size} as usize, {t});")

    def visit_Callback(self, n):
        params = ", ".join(self.visit(p) for p in n.prototype.parameters)
        if n.prototype.has_return_value:
            return_value = " -> i64"
        else:
            return_value = ""

        with self.collect_lines() as c:
            self.line(f"|{params}|{return_value}" " {")
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

        self.line(f"{return_value}solution::{method.name}({parameters});")

    def visit_Print(self, write_statement):
        format_string = " ".join("{}" for _ in write_statement.arguments)
        args = ", ".join(self.visit(v) for v in write_statement.arguments)
        self.line(f"println!(\"{format_string}\", {args});")

    def visit_Read(self, n):
        args = ", ".join(self.visit(v) for v in n.arguments)
        self.line(f"readln!({args});")

    def visit_If(self, n):
        condition = self.visit(n.condition)
        headers = [
            f"if {condition} != 0 {{",
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
        self.line(f"for {index_name} in 0..{size} {{")
        with self.indent():
            self.visit(s.body)
        self.line("}")

    def visit_Loop(self, n):
        self.line("loop {")
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
                self.line(f"if {condition} {{")
            else:
                self.line(f"}} else if {condition} {{")
            with self.indent():
                self.visit(case.body)
        self.line("}")

    def visit_Exit(self, n):
        self.line("std::process::exit(0);")

    def visit_Return(self, n):
        self.line(f"return {self.visit(n.value)};")

    def visit_Break(self, n):
        self.line("break;")

    def visit_Flush(self, n):
        self.line("std::io::stdout().flush().unwrap();")
