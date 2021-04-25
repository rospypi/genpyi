import errno
import os

import genmsg
import genmsg.msgs
from genmsg import MsgContext, MsgSpec, SrvSpec, gentools
from genpy.generator import compute_outfile_name, make_python_safe

from ._compat import lru_cache
from ._typing import TYPE_CHECKING
from .converter import convert_message_class, convert_service_class
from .stub_element import ClassElement, EmptyLinesElement, ImportsElement, ModuleElement

if TYPE_CHECKING:
    from typing import Callable, Dict, Iterator, List, TypeVar

    SpecType = TypeVar("SpecType", MsgSpec, SrvSpec)
    LoaderType = Callable[[MsgContext, str, str], SpecType]
    GeneratorType = Callable[[str, SpecType], Iterator[str]]


def generate_message_stub(package, spec):
    # type: (str, MsgSpec) -> Iterator[str]
    pyspec = make_python_safe(spec)
    imports = ImportsElement()
    genclass = convert_message_class(package, pyspec, imports)

    module = ModuleElement()
    module.add_element(imports)
    module.add_element(genclass)

    for line in module.generate():
        yield line


def generate_service_stub(package, spec):
    # type: (str, SrvSpec) -> Iterator[str]
    imports = ImportsElement()
    message_classes = []  # type: List[ClassElement]

    for message_spec in (spec.request, spec.response):
        pyspec = make_python_safe(message_spec)
        message_classes.append(convert_message_class(package, pyspec, imports))

    module = ModuleElement()
    module.add_element(imports)
    module.add_element(message_classes[0])  # request class
    module.add_element(EmptyLinesElement())
    module.add_element(message_classes[1])  # response class
    module.add_element(EmptyLinesElement())
    module.add_element(convert_service_class(spec))  # service class

    for line in module.generate():
        yield line


def _make_dirs(path):
    # type: (str) -> None
    # NOTE: This script will be executed in parallel.
    # So atomic operations are needed to avoid a race condition
    # e.g. Calling `makedir` after `exist` check might cause a race condition
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def _compute_outfile_path(outdir, target_path):
    # type: (str, str) -> str
    outpath = compute_outfile_name(
        outdir, os.path.basename(target_path), genmsg.EXT_MSG
    )  # type: str

    # Replace suffix .py with .pyi
    assert outpath.endswith(".py")
    outpath = outpath + "i"
    return outpath


def _load_spec(
    msg_context,  # type: MsgContext
    loader,  # type: LoaderType[SpecType]
    package,  # type: str
    target_path,  # type: str
    search_paths,  # type: Dict[str, List[str]]
):
    # type: (...) -> SpecType
    filename = os.path.basename(target_path)
    full_type = gentools.compute_full_type_name(package, filename)
    spec = loader(msg_context, target_path, full_type)

    # NOTE: We don't need to load dependency as we just emit the type information
    # The following lines are intended to just verify the message.
    try:
        genmsg.msg_loader.load_depends(msg_context, spec, search_paths)
    except genmsg.InvalidMsgSpec as e:
        raise RuntimeError("Failed to load message: {}".format(e))

    return spec


def generate_stub(
    msg_context,  # type: MsgContext
    loader,  # type: LoaderType[SpecType]
    generator,  # type: GeneratorType[SpecType]
    package,  # type: str
    target_path,  # type: str
    outdir,  # type: str
    search_paths,  # type: Dict[str, List[str]]
):
    # type: (...) -> str
    spec = _load_spec(msg_context, loader, package, target_path, search_paths)
    outpath = _compute_outfile_path(outdir, target_path)

    _make_dirs(outdir)
    with open(outpath, "w") as f:
        for line in generator(package, spec):
            f.write("{}\n".format(line))

    return outpath


@lru_cache()
def generate_pyi(outdir):
    # type: (str) -> None
    """Generate `__init__.pyi` to the given directory.

    .. warning::
        Make sure that `outdir` exists before calling this function.
    """
    path = os.path.join(outdir, "__init__.pyi")
    with open(path, "w"):
        pass
