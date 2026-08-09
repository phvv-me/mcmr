use super::{BTreeMap, Value, class, enriched, extracted, json};

#[test]
fn a_model_two_packages_import_proposes_the_file_below_the_package_they_share() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        ("shop/orders/__init__.py", ""),
        ("shop/billing/__init__.py", ""),
        (
            "shop/types.py",
            "from pydantic import BaseModel\n\n\nclass OrderLine(BaseModel):\n    total: int\n",
        ),
        (
            "shop/orders/place.py",
            "from ..types import OrderLine\n\n\ndef place(line: OrderLine) -> int:\n    return line.total\n",
        ),
        (
            "shop/billing/charge.py",
            "from ..types import OrderLine\n\n\ndef charge(line: OrderLine) -> int:\n    return line.total\n",
        ),
    ]);
    let model = class(&classes, "OrderLine");

    assert_eq!(model["is_declarative_model"], true);
    assert_eq!(model["has_ordinary_behavior"], false);
    assert_eq!(
        model["importing_modules"],
        json!(["shop.billing.charge", "shop.orders.place"])
    );
    assert_eq!(
        model["proposed_model_destination"],
        "shop/models/order_line.py"
    );
}

#[test]
fn a_model_one_package_imports_proposes_that_package_own_models_module() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        ("shop/orders/__init__.py", ""),
        (
            "shop/orders/types.py",
            "from pydantic import BaseModel\n\n\nclass OrderLine(BaseModel):\n    total: int\n",
        ),
        (
            "shop/orders/place.py",
            "from .types import OrderLine\n\n\ndef place(line: OrderLine) -> int:\n    return line.total\n",
        ),
        (
            "shop/orders/audit.py",
            "from .types import OrderLine\n\n\ndef audit(line: OrderLine) -> int:\n    return line.total\n",
        ),
    ]);

    assert_eq!(
        class(&classes, "OrderLine")["proposed_model_destination"],
        "shop/orders/models.py"
    );
}

#[test]
fn tests_do_not_claim_ownership_of_a_production_model() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/types.py",
            "from pydantic import BaseModel\n\n\nclass OrderLine(BaseModel):\n    total: int\n",
        ),
        ("tests/__init__.py", ""),
        (
            "tests/test_orders.py",
            "from shop.types import OrderLine\n\n\ndef test_order():\n    assert OrderLine(total=1)\n",
        ),
        (
            "tests/test_billing.py",
            "from shop.types import OrderLine\n\n\ndef test_charge():\n    assert OrderLine(total=1)\n",
        ),
    ]);
    let model = class(&classes, "OrderLine");

    assert_eq!(
        model["importing_modules"],
        json!(["tests.test_billing", "tests.test_orders"])
    );
    assert_eq!(model["proposed_model_destination"], "");
}

#[test]
fn dotted_root_filenames_do_not_invent_a_package_directory() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/types.py",
            "from pydantic import BaseModel\n\n\nclass OrderLine(BaseModel):\n    total: int\n",
        ),
        (
            "consumer.one.py",
            "from shop.types import OrderLine\n\n\ndef first(line: OrderLine) -> int:\n    return line.total\n",
        ),
        (
            "consumer.two.py",
            "from shop.types import OrderLine\n\n\ndef second(line: OrderLine) -> int:\n    return line.total\n",
        ),
    ]);

    assert_eq!(
        class(&classes, "OrderLine")["proposed_model_destination"],
        ""
    );
}

#[test]
fn a_model_foundation_and_a_property_service_are_not_records_to_move() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/bases.py",
            "from pydantic import BaseModel\n\n\nclass Model(BaseModel):\n    pass\n",
        ),
        (
            "shop/discovery.py",
            "from functools import cached_property\nfrom .bases import Model\n\n\nclass Discovery(Model):\n    package: str\n\n    @cached_property\n    def modules(self):\n        return []\n",
        ),
    ]);

    assert_eq!(class(&classes, "Model")["is_declarative_model"], false);
    assert_eq!(class(&classes, "Discovery")["is_declarative_model"], true);
    assert_eq!(class(&classes, "Discovery")["has_ordinary_behavior"], true);
}

#[test]
fn a_configuration_base_is_the_foundation_wherever_a_project_keeps_it() {
    // A foundation used to be recognized by the file name `bases.py`, so the same class held in
    // `core/base/strict.py` was reported as a model deriving Pydantic directly.
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        ("shop/core/__init__.py", ""),
        (
            "shop/core/strict.py",
            "from pydantic import BaseModel, ConfigDict\n\n\nclass Model(BaseModel):\n    model_config = ConfigDict(frozen=True)\n",
        ),
        (
            "shop/orders.py",
            "from .core.strict import Model\n\n\nclass Order(Model):\n    total: int\n",
        ),
        (
            "shop/settings.py",
            "from pydantic import BaseModel\n\n\nclass Settings(BaseModel):\n    retries: int\n",
        ),
    ]);
    let foundation = class(&classes, "Model");

    assert_eq!(foundation["states_model_configuration"], true);
    assert_eq!(foundation["is_declarative_model"], false);
    assert_eq!(foundation["directly_inherits_pydantic_base_model"], false);
    assert_eq!(class(&classes, "Order")["is_declarative_model"], true);
    assert_eq!(
        class(&classes, "Settings")["directly_inherits_pydantic_base_model"],
        true
    );
}

#[test]
fn model_policy_is_established_by_owning_a_foundation_rather_than_by_a_folder_name() {
    let owned = extracted(&[
        ("shop/__init__.py", ""),
        (
            "shop/core.py",
            "from pydantic import BaseModel, ConfigDict\n\n\nclass Model(BaseModel):\n    model_config = ConfigDict(frozen=True)\n",
        ),
        (
            "shop/orders.py",
            "from .core import Model\n\n\nclass Order(Model):\n    total: int\n",
        ),
    ]);
    let named = extracted(&[
        ("shop/__init__.py", ""),
        ("shop/bases/__init__.py", ""),
        (
            "shop/bases/text.py",
            "def clean(value):\n    return value.strip()\n",
        ),
        (
            "shop/orders.py",
            "from pydantic import BaseModel\nfrom .bases.text import clean\n\n\nclass Order(BaseModel):\n    total: int\n",
        ),
    ]);
    let established = |facts: &BTreeMap<String, Vec<Value>>| {
        facts["ClassFact"]
            .iter()
            .any(|fact| fact["has_approved_model_foundation_policy"] == json!(true))
    };

    assert!(established(&owned));
    assert!(!established(&named));
}

#[test]
fn a_model_remains_declarative_below_a_project_owned_intermediate_base() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        (
            "shop/bases.py",
            "from patos import FrozenModel\n\n\nclass Fact(FrozenModel):\n    pass\n",
        ),
        (
            "shop/facts.py",
            "from .bases import Fact\n\n\nclass OrderFact(Fact):\n    total: int\n",
        ),
    ]);

    assert_eq!(class(&classes, "OrderFact")["is_declarative_model"], true);
}

#[test]
fn two_short_role_types_two_modules_import_together_propose_one_namespace() {
    let sources = [
        ("shop/__init__.py", ""),
        (
            "shop/message.py",
            "class MessageContent:\n    pass\n\n\nclass MessageKind:\n    pass\n",
        ),
        (
            "shop/api.py",
            "from .message import MessageContent, MessageKind\n\n\ndef read(content: MessageContent, kind: MessageKind) -> None:\n    return None\n",
        ),
        (
            "shop/jobs.py",
            "from .message import MessageContent, MessageKind\n\n\ndef sweep(content: MessageContent, kind: MessageKind) -> None:\n    return None\n",
        ),
    ];
    let facts = extracted(&sources);
    let group = facts["ClassFact"]
        .iter()
        .flat_map(|fact| {
            fact["coupled_groups"]
                .as_array()
                .cloned()
                .unwrap_or_default()
        })
        .next()
        .expect("the group is proposed");

    assert_eq!(
        json!([
            group["prefix"],
            group["role_suffixes"],
            group["type_count"],
            group["coimporting_module_count"],
        ]),
        json!(["Message", ["Content", "Kind"], 2, 2])
    );
}

#[test]
fn a_nested_model_collects_no_importers_and_is_proposed_nowhere() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        ("shop/orders/__init__.py", ""),
        ("shop/billing/__init__.py", ""),
        (
            "shop/types.py",
            "from patos import FrozenModel\n\n\nclass Holder:\n    class OrderLine(FrozenModel):\n        total: int\n",
        ),
        (
            "shop/orders/place.py",
            "from ..types import OrderLine\n\n\ndef place(line: OrderLine) -> int:\n    return line.total\n",
        ),
        (
            "shop/billing/charge.py",
            "from ..types import OrderLine\n\n\ndef charge(line: OrderLine) -> int:\n    return line.total\n",
        ),
    ]);
    let model = class(&classes, "OrderLine");

    assert_eq!(model["is_declarative_model"], true);
    assert_eq!(model["importing_modules"], json!([] as [&str; 0]));
    assert_eq!(model["proposed_model_destination"], "");
}

#[test]
fn a_class_that_runs_behavior_is_never_proposed_for_a_shared_models_package() {
    let classes = enriched(&[
        ("shop/__init__.py", ""),
        ("shop/orders/__init__.py", ""),
        ("shop/billing/__init__.py", ""),
        (
            "shop/clients.py",
            "from patos import FrozenModel\n\n\nclass Catalog(FrozenModel):\n    host: str\n\n    def fetch(self, name):\n        return self.host + name\n\n\nclass OrderLine(FrozenModel):\n    total: int\n",
        ),
        (
            "shop/orders/place.py",
            "from ..clients import Catalog, OrderLine\n\n\ndef place(held: Catalog, line: OrderLine) -> int:\n    return line.total\n",
        ),
        (
            "shop/billing/charge.py",
            "from ..clients import Catalog, OrderLine\n\n\ndef charge(held: Catalog, line: OrderLine) -> int:\n    return line.total\n",
        ),
    ]);
    let client = class(&classes, "Catalog");
    let model = class(&classes, "OrderLine");

    // The client is imported exactly as widely as the model, so the gate is what suppresses it.
    assert_eq!(
        client["importing_modules"],
        json!(["shop.billing.charge", "shop.orders.place"])
    );
    assert_eq!(client["has_ordinary_behavior"], true);
    assert_eq!(client["proposed_model_destination"], "");
    assert_eq!(model["has_ordinary_behavior"], false);
    assert_eq!(
        model["proposed_model_destination"],
        "shop/models/order_line.py"
    );
}
