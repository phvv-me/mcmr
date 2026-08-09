use super::{class, enriched, json};

#[test]
fn a_base_kept_only_for_one_subclass_states_every_half_of_that_proof() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/support.py",
            "class ServiceSupport:\n    def normalize(self, value):\n        return value.strip()\n",
        ),
        (
            "shop/service.py",
            "from .support import ServiceSupport\n\n\nclass Service(ServiceSupport):\n    pass\n",
        ),
    ]);
    let base = class(&classes, "ServiceSupport");

    assert_eq!(base["direct_subclasses"], json!(["Service"]));
    assert_eq!(base["descendant_count"], 1);
    assert_eq!(base["is_instantiated"], false);
    assert_eq!(base["is_exported"], false);
    assert_eq!(base["only_cross_module_reference_is_subclass"], true);
    assert_eq!(
        class(&classes, "Service")["base_is_removable_overlap"],
        true
    );
}

#[test]
fn a_subclass_imported_through_an_explicit_package_export_reaches_its_base() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/contracts/__init__.py",
            "from .source import ServiceBase\n\n__all__ = ['ServiceBase']\n",
        ),
        ("shop/contracts/source.py", "class ServiceBase:\n    pass\n"),
        (
            "shop/service.py",
            "from .contracts import ServiceBase\n\n\nclass Service(ServiceBase):\n    pass\n",
        ),
    ]);

    assert_eq!(
        class(&classes, "ServiceBase")["direct_subclasses"],
        json!(["Service"])
    );
    assert_eq!(class(&classes, "ServiceBase")["descendant_count"], 1);
}

#[test]
fn a_base_somebody_builds_or_exports_is_not_kept_only_for_its_subclass() {
    let classes = enriched(&[
        ("shop/__init__.py", "from .support import ServiceSupport\n"),
        (
            "shop/support.py",
            "class ServiceSupport:\n    def normalize(self, value):\n        return value\n",
        ),
        (
            "shop/service.py",
            "from .support import ServiceSupport\n\n\nclass Service(ServiceSupport):\n    pass\n\n\nheld = ServiceSupport()\n",
        ),
    ]);
    let base = class(&classes, "ServiceSupport");

    assert_eq!(base["is_instantiated"], true);
    assert_eq!(base["is_exported"], true);
    assert_eq!(base["only_cross_module_reference_is_subclass"], false);
}

#[test]
fn a_base_exported_by_its_own_module_is_not_proposed_for_removal() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/support.py",
            "__all__ = ['ServiceSupport']\n\n\nclass ServiceSupport:\n    pass\n",
        ),
        (
            "shop/service.py",
            "from .support import ServiceSupport\n\n\nclass Service(ServiceSupport):\n    pass\n",
        ),
    ]);

    assert_eq!(
        class(&classes, "Service")["base_is_removable_overlap"],
        false
    );
}

#[test]
fn two_bases_supplying_one_concrete_method_are_an_order_sensitive_hierarchy() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/loaders.py",
            "class JsonLoader:\n    def load(self):\n        return 1\n\n\nclass CachedLoader:\n    def load(self):\n        return 2\n\n\nclass Service(JsonLoader, CachedLoader):\n    pass\n\n\nclass Polite(JsonLoader, CachedLoader):\n    def load(self):\n        return super().load()\n",
        ),
    ]);

    assert_eq!(
        class(&classes, "Service")["has_noncooperative_concrete_collision"],
        true
    );
    assert_eq!(
        class(&classes, "Service")["has_redundant_direct_base"],
        false
    );
}

#[test]
fn a_base_that_already_inherits_another_base_is_a_redundant_direct_edge() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/layers.py",
            "class Contract:\n    def run(self):\n        return 1\n\n\nclass Middle(Contract):\n    def other(self):\n        return 2\n\n\nclass Leaf(Middle, Contract):\n    pass\n",
        ),
    ]);

    assert_eq!(class(&classes, "Leaf")["has_redundant_direct_base"], true);
}

#[test]
fn a_subclass_carries_state_owned_by_any_resolved_ancestor() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/bases.py",
            "from patos import FrozenModel\n\n\nclass Record(FrozenModel):\n    value: int\n",
        ),
        (
            "shop/orders.py",
            "from .bases import Record\n\n\nclass Order(Record):\n    pass\n\n\nclass SpecialOrder(Order):\n    pass\n",
        ),
    ]);

    assert_eq!(class(&classes, "Order")["has_inherited_fields"], true);
    assert_eq!(
        class(&classes, "SpecialOrder")["has_inherited_fields"],
        true
    );
}

#[test]
fn a_class_this_repository_never_heard_of_leaves_the_record_alone() {
    let classes = enriched(&[("alone.py", "class Report:\n    pass\n")]);

    assert_eq!(class(&classes, "Report")["descendant_count"], 0);
    assert_eq!(
        class(&classes, "Report")["direct_subclasses"],
        json!([] as [&str; 0])
    );
}

#[test]
fn a_nested_class_inherits_the_sibling_declared_beside_it_in_the_same_container() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/groups.py",
            "from patos import FrozenModel\n\n\nclass ReachFields:\n    class Identity(FrozenModel):\n        qualname: str\n\n    class Declaration(Identity):\n        scope: str\n\n    class Ownership(Declaration):\n        owner: str\n",
        ),
    ]);

    assert_eq!(
        class(&classes, "Identity")["direct_subclasses"],
        json!(["Declaration"])
    );
    assert_eq!(class(&classes, "Declaration")["is_declarative_model"], true);
    assert_eq!(class(&classes, "Declaration")["has_inherited_fields"], true);
    assert_eq!(class(&classes, "Ownership")["is_declarative_model"], true);
    assert_eq!(class(&classes, "Ownership")["descendant_count"], 0);
    assert_eq!(class(&classes, "Identity")["descendant_count"], 2);
}

#[test]
fn a_nested_class_inherits_the_foundation_its_module_imported_from_elsewhere() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/bases.py",
            "from patos import FrozenModel\n\n\nclass Fact(FrozenModel):\n    pass\n",
        ),
        (
            "shop/groups.py",
            "from .bases import Fact\n\n\nclass FunctionFields:\n    class Execution(Fact):\n        total: int\n",
        ),
    ]);

    assert_eq!(class(&classes, "Execution")["is_declarative_model"], true);
    assert_eq!(
        class(&classes, "Fact")["direct_subclasses"],
        json!(["Execution"])
    );
}

#[test]
fn a_bare_base_name_reaches_the_module_level_binding_rather_than_a_nested_class() {
    // Two classes can now share one bare name in one module, so a base written against the name a
    // module binds has to keep reaching that binding rather than the class nested inside another.
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/records.py",
            "from patos import FrozenModel\n\n\nclass Record(FrozenModel):\n    total: int\n",
        ),
        (
            "shop/reports.py",
            "from .records import Record\n\n\nclass Wrapper:\n    class Record:\n        pass\n\n\nclass Report(Record):\n    pass\n",
        ),
    ]);

    assert_eq!(class(&classes, "Report")["is_declarative_model"], true);
    assert_eq!(class(&classes, "Report")["has_inherited_fields"], true);
}

#[test]
fn a_top_level_class_wins_the_bare_name_a_nested_class_of_its_module_repeats() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/orders.py",
            "from patos import FrozenModel\n\n\nclass Order(FrozenModel):\n    total: int\n\n\nclass Holder:\n    class Order:\n        pass\n",
        ),
        (
            "shop/special.py",
            "from .orders import Order\n\n\nclass SpecialOrder(Order):\n    pass\n",
        ),
    ]);

    assert_eq!(
        class(&classes, "SpecialOrder")["is_declarative_model"],
        true
    );
    assert_eq!(
        class(&classes, "SpecialOrder")["has_inherited_fields"],
        true
    );
    assert_eq!(
        class(&classes, "Order")["direct_subclasses"],
        json!(["SpecialOrder"])
    );
}
