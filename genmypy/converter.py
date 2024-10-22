import genmsg
import genmsg.msgs
from genmsg import MsgSpec, SrvSpec
from genpy.generator import compute_pkg_type

from ._compat import lru_cache
from ._typing import TYPE_CHECKING
from .stub_element import (
    AliasElement,
    ClassElement,
    ClassMethodElement,
    CommentElement,
    EmptyLinesElement,
    FieldElement,
    ImportsElement,
    ParameterElement,
)

if TYPE_CHECKING:
    from typing import Dict, List, Sequence, Tuple


_GENMSG_PRIMITIVES = {
    "byte": "int",
    "char": "str",
    "int8": "int",
    "int16": "int",
    "int32": "int",
    "int64": "int",
    "uint8": "int",
    "uint16": "int",
    "uint32": "int",
    "uint64": "int",
    "float32": "float",
    "float64": "float",
    "bool": "bool",
    "string": "str",
}

_GENPY_DEFINED = {
    genmsg.HEADER: ("std_msgs.msg._Header.Header", "std_msgs.msg._Header"),
    genmsg.TIME: ("genpy.Time", "genpy"),
    genmsg.DURATION: ("genpy.Duration", "genpy"),
}  # type: Dict[str, Tuple[str, str]]


@lru_cache()
def _get_genmsg_type(first_party_package, field_type, imports):
    # type: (str, str, ImportsElement) -> str

    """Get the corresponding python type for the given ROS type.

    .. warning::
        As this method is decorated by lru_cache, make sure that
        you are using another instance of ImportsElement when
        calling this method in a different context.
        (e.g. creating a different module)
    """
    primitive = _GENMSG_PRIMITIVES.get(field_type)
    if primitive is not None:
        return primitive

    if field_type.endswith("]"):
        base_field_type, is_array, array_len = genmsg.msgs.parse_type(field_type)
        assert is_array
        # TODO: Handle array_len (use typing.Annotated?)

        if base_field_type == "uint8":
            # Special case for uint8[]
            return "bytes"

        base_type = _get_genmsg_type(first_party_package, base_field_type, imports)
        return "typing.List[{}]".format(base_type)

    special = _GENPY_DEFINED.get(field_type)
    if special is not None:
        full_name, module = special
        imports.add_third_party_module(module, None)
        return full_name

    package, type_ = compute_pkg_type(first_party_package, field_type)
    module = "{}.msg".format(package)
    imports.add_third_party_module(module, None)

    return "{}.{}".format(module, type_)


def _convert_message_fields(first_party_package, spec, imports):
    # type: (str, MsgSpec, ImportsElement) -> List[FieldElement]
    fields = []  # type: List[FieldElement]
    for field in spec.fields():
        type_, name = field
        fields.append(
            FieldElement(
                name,
                _get_genmsg_type(first_party_package, type_, imports),
            )
        )

    return fields


def _convert_message_constants(first_party_package, spec, imports):
    # type: (str, MsgSpec, ImportsElement) -> List[FieldElement]
    constants = []  # type: List[FieldElement]
    for constant in spec.constants:
        constants.append(
            FieldElement(
                constant.name,
                _get_genmsg_type(first_party_package, constant.type, imports),
            )
        )

    return constants


def convert_message_class(first_party_package, spec, imports):
    # type: (str, MsgSpec, ImportsElement) -> ClassElement
    imports.add_third_party_module("genpy", None)
    imports.add_system_module("typing", None)
    imports.add_system_module("types", None)

    msgclass = ClassElement(spec.short_name, "genpy.Message")

    # Add private fields
    msgclass.add(FieldElement("_md5sum", "str"))
    msgclass.add(FieldElement("_type", "str"))
    msgclass.add(FieldElement("_has_header", "bool"))
    msgclass.add(FieldElement("_full_text", "str"))
    msgclass.add(FieldElement("__slots__", "typing.List[str]"))
    msgclass.add(FieldElement("_slot_types", "typing.List[str]"))

    message_constants = _convert_message_constants(first_party_package, spec, imports)
    if len(message_constants) > 0:
        msgclass.add(EmptyLinesElement())
        msgclass.add(CommentElement("Constants"))
        for c in message_constants:
            msgclass.add(c)

    message_fields = _convert_message_fields(first_party_package, spec, imports)
    if len(message_fields) > 0:
        msgclass.add(EmptyLinesElement())
        msgclass.add(CommentElement("Fields"))
        for f in message_fields:
            msgclass.add(f)

    msgclass.add(EmptyLinesElement())

    # Add __init__ method that accepts message fields as the parameter
    init_method = ClassMethodElement("__init__", "None")
    for field in message_fields:
        init_method.add_parameter(
            ParameterElement(field.name, field.type, has_default=True)
        )

    # NOTE: Emit *args and **kwds in order to align with the actual implementation
    init_method.add_parameter(ParameterElement("*args", "typing.Any"))
    init_method.add_parameter(ParameterElement("**kwds", "typing.Any"))

    msgclass.add(init_method)

    # Add private methods except pattern methods like `_get_struct_I`
    msgclass.add(ClassMethodElement("_get_types", "typing.List[str]"))

    # Add public methods
    msgclass.add(
        ClassMethodElement(
            "serialize", "None", [ParameterElement("buff", "typing.BinaryIO")]
        )
    )
    msgclass.add(
        ClassMethodElement(
            "deserialize", spec.short_name, [ParameterElement("str", "bytes")]
        )
    )
    msgclass.add(
        ClassMethodElement(
            "serialize_numpy",
            "None",
            [
                ParameterElement("buff", "typing.BinaryIO"),
                ParameterElement("numpy", "types.ModuleType"),
            ],
        )
    )
    msgclass.add(
        ClassMethodElement(
            "deserialize_numpy",
            spec.short_name,
            [
                ParameterElement("str", "bytes"),
                ParameterElement("numpy", "types.ModuleType"),
            ],
        )
    )

    return msgclass


def convert_service_class(spec, request_class, response_class):
    # type: (SrvSpec, ClassElement, ClassElement) -> ClassElement
    srvclass = ClassElement(spec.short_name, "object")
    srvclass.add(FieldElement("_type", "str"))
    srvclass.add(FieldElement("_md5sum", "str"))
    srvclass.add(AliasElement("_request_class", request_class.name))
    srvclass.add(AliasElement("_response_class", response_class.name))

    return srvclass


def convert_genpy_init(modules):
    # type: (Sequence[str]) -> ImportsElement
    imports = ImportsElement()
    for m in modules:
        imports.add_third_party_module("._{}".format(m), "*")

    return imports
