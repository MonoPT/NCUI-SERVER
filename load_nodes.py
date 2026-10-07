import importlib
import pkgutil
import pathlib
import sys
import inspect
import importlib.util
import pathlib

from node import Node

def load_all_packages(folder_path):
    """
    Find and import all Python modules/packages inside a folder.

    Args:
        folder_path (str): Path to folder containing .py files or packages.

    Returns:
        dict: {module_name: imported_module}
    """
    folder = pathlib.Path(folder_path).resolve()

    if not folder.is_dir():
        raise ValueError(f"Invalid folder: {folder}")

    # Temporarily add folder to sys.path
    sys.path.insert(0, str(folder))

    loaded = {}

    try:
        for module_info in pkgutil.iter_modules([str(folder)]):
            name = module_info.name
            try:
                module = importlib.import_module(name)
                loaded[name] = module
                print(f"Loaded: {name}")
            except Exception as e:
                print(f"Failed: {name} -> {e}")
    finally:
        sys.path.pop(0)

    return loaded

def load_all_recursive(folder_path):
    folder = pathlib.Path(folder_path).resolve()
    project_root = folder.parent  # this is critical

    if not folder.is_dir():
        raise ValueError(f"Invalid folder: {folder}")

    modules = {}

    for py_file in folder.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue

        # Build correct module name from project root
        rel_path = py_file.relative_to(project_root).with_suffix("")
        module_name = ".".join(rel_path.parts)

        # Fix __init__ → package name
        if module_name.endswith(".__init__"):
            module_name = module_name[: -len(".__init__")]

        spec = importlib.util.spec_from_file_location(module_name, py_file)

        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)

        # CRITICAL: register before execution
        sys.modules[module_name] = module

        spec.loader.exec_module(module)

        modules[module_name] = module
        print(f"Loaded: {module_name}")

    return modules
    
def instantiate_subclasses(modules, base_class) -> list[Node]:
    """
    Finds subclasses of base_class in modules and instantiates them.

    Args:
        modules (dict): {module_name: module_object}
        base_class (type): base class to filter subclasses

    Returns:
        list: instantiated objects
    """
    instances = []

    for module_name, module in modules.items():

        for _, obj in inspect.getmembers(module, inspect.isclass):

            # ensure class belongs to this module
            if obj.__module__ != module.__name__:
                continue

            try:
                if issubclass(obj, base_class) and obj is not base_class:
                    try:
                        instance = obj()  # instantiate
                        instances.append(instance)
                    except Exception:
                        # skip classes that require constructor args
                        continue
            except TypeError:
                continue

    return instances
  
def load_nodes():
    return instantiate_subclasses(load_all_recursive("./nodes"), Node)
  
__all__ = ["load_nodes"]