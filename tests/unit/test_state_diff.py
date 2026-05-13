from app.core.oop_model import ClassDef, MemberDef, ObjectInstance, OopModel
from app.core.state_diff import StateDiff, ClassError


class TestStateDiff:
    def test_empty_diff_is_empty(self):
        diff = StateDiff()
        assert diff.is_empty is True

    def test_diff_with_class_is_not_empty(self):
        diff = StateDiff(added_classes=[ClassDef("Player")])
        assert diff.is_empty is False

    def test_diff_with_instance_is_not_empty(self):
        diff = StateDiff(added_instances=[ObjectInstance("Player", "p")])
        assert diff.is_empty is False

    def test_diff_with_error_is_not_empty(self):
        diff = StateDiff(errors=[ClassError("test", "something wrong")])
        assert diff.is_empty is False

    def test_class_error_fields(self):
        err = ClassError("redefinition", "类已存在", "Player", 3)
        assert err.kind == "redefinition"
        assert err.description == "类已存在"
        assert err.class_name == "Player"
        assert err.line == 3
