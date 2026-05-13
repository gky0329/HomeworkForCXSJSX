from app.core.oop_model import ClassDef, MemberDef, ObjectInstance, OopModel


class TestOopModel:
    def test_class_def_creation(self):
        cd = ClassDef(name="Player", members=[MemberDef("health", "int", "public")])
        assert cd.name == "Player"
        assert cd.has_member("health") is True
        assert cd.has_member("score") is False
        assert cd.get_member("health").type == "int"

    def test_object_instance_creation(self):
        inst = ObjectInstance(cls_name="Player", var_name="p")
        assert inst.cls_name == "Player"
        assert inst.var_name == "p"

    def test_oop_model_add_class(self):
        model = OopModel()
        cd = ClassDef(name="Player")
        model.add_class(cd)
        assert model.get_class("Player") is cd
        assert model.get_class("Nonexistent") is None

    def test_oop_model_add_instance(self):
        model = OopModel()
        inst = ObjectInstance(cls_name="Player", var_name="p", values={"health": 20})
        model.add_instance(inst)
        assert model.get_instance("p") is inst
        assert model.get_instance("q") is None

    def test_oop_model_remove_instance(self):
        model = OopModel()
        inst = ObjectInstance(cls_name="Player", var_name="p")
        model.add_instance(inst)
        model.remove_instance("p")
        assert model.get_instance("p") is None

    def test_oop_model_snapshot_is_independent(self):
        model = OopModel()
        cd = ClassDef("Player")
        model.add_class(cd)
        snap = model.snapshot()
        model.add_instance(ObjectInstance("Player", "p"))
        assert snap.get_instance("p") is None
        assert model.get_instance("p") is not None

    def test_oop_model_reset(self):
        model = OopModel()
        model.add_class(ClassDef("Player"))
        model.add_instance(ObjectInstance("Player", "p"))
        model.reset()
        assert len(model.classes) == 0
        assert len(model.instances) == 0
