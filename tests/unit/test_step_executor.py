from app.core.oop_model import ClassDef, MemberDef, ObjectInstance, OopModel
from app.core.step_executor import execute_line


class TestStepExecutor:
    def setup_method(self):
        self.model = OopModel()

    def test_class_definition(self):
        diff = execute_line("class Player {", 0, self.model)
        assert len(diff.added_classes) == 1
        assert diff.added_classes[0].name == "Player"
        assert "Player" in self.model.classes
        assert self.model._in_class_body is True

    def test_class_redefinition_error(self):
        execute_line("class Creeper {", 0, self.model)
        execute_line("};", 1, self.model)
        diff = execute_line("class Creeper {", 2, self.model)
        assert len(diff.errors) == 1
        assert diff.errors[0].kind == "redefinition"

    def test_member_declaration_inside_class(self):
        execute_line("class Player {", 0, self.model)
        diff = execute_line("    int health;", 1, self.model)
        assert self.model._current_class is not None
        assert self.model._current_class.has_member("health")
        assert len(self.model._current_class.members) == 1

    def test_instance_creation(self):
        lines = ["class Player {", "public:", "    int health;", "};"]
        for i, line in enumerate(lines):
            execute_line(line, i, self.model)

        diff = execute_line("Player p;", len(lines), self.model)
        assert len(diff.added_instances) == 1
        assert diff.added_instances[0].var_name == "p"
        assert "p" in self.model.instances
        assert self.model.instances["p"].values["health"] == 0

    def test_instance_missing_class_error(self):
        diff = execute_line("Player p;", 0, self.model)
        assert len(diff.errors) == 1
        assert diff.errors[0].kind == "missing_class"

    def test_member_assignment(self):
        lines = ["class Player {", "    int health;", "};", "Player p;"]
        for i, line in enumerate(lines):
            execute_line(line, i, self.model)

        diff = execute_line("p.health = 20;", len(lines), self.model)
        assert len(diff.updated_instances) == 1
        assert diff.updated_instances[0] == ("p", "health", 20)
        assert self.model.instances["p"].values["health"] == 20

    def test_scope_exit_removes_instances(self):
        lines = ["class Player {", "    int health;", "};", "Player p;"]
        for i, line in enumerate(lines):
            execute_line(line, i, self.model)

        diff = execute_line("}", len(lines), self.model)
        assert len(diff.removed_instances) == 1
        assert "p" in diff.removed_instances
        assert "p" not in self.model.instances

    def test_full_flow_two_classes(self):
        model = OopModel()
        lines = [
            "class Creeper {",
            "public:",
            "    int health;",
            "};",
            "class IronGolem {",
            "public:",
            "    int health;",
            "};",
            "Creeper c;",
            "IronGolem g;",
            "c.health = 30;",
            "g.health = 50;",
        ]
        for i, line in enumerate(lines):
            execute_line(line, i, model)

        assert len(model.classes) == 2
        assert len(model.instances) == 2
        assert model.instances["c"].values["health"] == 30
        assert model.instances["g"].values["health"] == 50

    def test_comment_lines_ignored(self):
        diff = execute_line("// this is a comment", 0, self.model)
        assert diff.is_empty is True

    def test_empty_lines_ignored(self):
        diff = execute_line("", 0, self.model)
        assert diff.is_empty is True

    def test_private_access_violation(self):
        lines = ["class Player {", "private:", "    int health;", "};", "Player p;"]
        for i, line in enumerate(lines):
            execute_line(line, i, self.model)

        diff = execute_line("p.health = 20;", len(lines), self.model)
        assert len(diff.errors) == 1
        assert diff.errors[0].kind == "access_violation"
